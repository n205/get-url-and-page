import logging
import os
import shutil
import tempfile
import uuid
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import numpy as np


def update_pdf_links(worksheet, existing_df, processed_urls):
    driver = None
    # 完全なユニークパスを生成
    run_id = str(uuid.uuid4())
    user_data_dir = f"/tmp/chrome_user_data_{run_id}"
    data_path = f"/tmp/chrome_data_path_{run_id}"
    disk_cache_dir = f"/tmp/chrome_cache_{run_id}"

    os.makedirs(user_data_dir, exist_ok=True)

    try:
        options = Options()
        # --- クラッシュとロック競合を絶対に回避する強力オプション ---
        options.add_argument('--headless')  # あえて従来の安定した --headless を指定（=newは競合の元）
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # ロック誤判定を防ぐための必須設定
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-translate')
        options.add_argument('--hide-scrollbars')
        options.add_argument('--metrics-recording-only')
        options.add_argument('--mute-audio')
        options.add_argument('--safebrowsing-disable-auto-update')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors-spki-list')

        # 完全個別ディレクトリ設定
        options.add_argument(f'--user-data-dir={user_data_dir}')
        options.add_argument(f'--data-path={data_path}')
        options.add_argument(f'--disk-cache-dir={disk_cache_dir}')
        options.add_argument(f'--homedir={user_data_dir}')

        options.binary_location = "/usr/local/bin/google-chrome"
        service = Service(executable_path="/usr/local/bin/chromedriver")

        # Selenium起動
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)

        url = 'https://jpx.esgdata.jp/app?分類=統合報告書'
        driver.get(url)
        time.sleep(10)

        anchors = driver.find_elements(By.CSS_SELECTOR, 'a[target="_blank"]')
        new_rows = []
        seen_urls = set()

        for a in anchors:
            href = a.get_attribute('href')
            if href and href.endswith('.pdf') and href not in processed_urls and href not in seen_urls:
                seen_urls.add(href)
                new_rows.append({
                    'URL': href,
                })

        if new_rows:
            new_df = pd.DataFrame(new_rows)
            new_df.replace([np.nan, np.inf, -np.inf], '', inplace=True)
            worksheet.append_rows(new_df.values.tolist())
            logging.info(f'🆕 新規URL {len(new_rows)} 件を追加しました')
            return f'{len(new_rows)} 件のURLを追加', 200
        else:
            logging.info('📄 新規URLはありませんでした')
            return '追加対象なし', 200

    except Exception as e:
        import traceback
        logging.error('❌ PDFリンク取得エラー:\n' + traceback.format_exc())
        return f'エラー: {e}', 500

    finally:
        # プロセスの終了
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        
        # 作成した全フォルダの確実なクリーンアップ
        for folder in [user_data_dir, data_path, disk_cache_dir]:
            if os.path.exists(folder):
                try:
                    shutil.rmtree(folder, ignore_errors=True)
                except Exception:
                    pass
