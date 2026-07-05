import logging
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account

import os
import shutil
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import numpy as np


def update_pdf_links(worksheet, existing_df, processed_urls):
    driver = None
    # 1. 完全に重ならない専用の一時ディレクトリをシステムに作成させる
    user_data_dir = tempfile.mkdtemp(prefix="chrome_user_data_")
    disk_cache_dir = tempfile.mkdtemp(prefix="chrome_cache_")

    try:
        options = Options()
        # --- ヘッドレス環境の安定化オプション ---
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--single-process')
        options.add_argument('--remote-debugging-port=9222')

        # --- コンテナ環境のロック・ポップアップ回避フラグ ---
        options.add_argument('--disable-background-networking')
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-extensions')

        # 2. 上記で作成した完全にフレッシュなパスを割り当てる
        options.add_argument(f'--user-data-dir={user_data_dir}')
        options.add_argument(f'--disk-cache-dir={disk_cache_dir}')

        options.binary_location = "/usr/local/bin/google-chrome"
        service = Service(executable_path="/usr/local/bin/chromedriver")

        # ブラウザ起動
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)

        url = 'https://jpx.esgdata.jp/app?分類=統合報告書'
        driver.get(url)
        time.sleep(5)

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
        # 3. ブラウザプロセスを確実に終了
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        
        # 4. 【重要】使用した一時ディレクトリをロックファイルごと完全に物理削除（メモリ解放＆次回起動時の衝突防止）
        for folder in [user_data_dir, disk_cache_dir]:
            if os.path.exists(folder):
                try:
                    shutil.rmtree(folder, ignore_errors=True)
                except Exception as e:
                    logging.warning(f"一時フォルダの削除に失敗しました: {e}")
