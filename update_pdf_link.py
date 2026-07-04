import logging
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account

import os
import shutil
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import numpy as np


def update_pdf_links(worksheet, existing_df, processed_urls):
    driver = None
    # 完全にユニークな作業ディレクトリを作成
    session_id = str(uuid.uuid4())
    unique_user_data_dir = f"/tmp/chrome_user_data_{session_id}"
    unique_cache_dir = f"/tmp/chrome_cache_{session_id}"
    
    try:
        os.makedirs(unique_user_data_dir, exist_ok=True)
        os.makedirs(unique_cache_dir, exist_ok=True)

        # --- Cloud Run 専用の超安定・クラッシュ防止 Selenium オプション ---
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage') # /dev/shmの代わりに/tmpを使う
        options.add_argument('--disable-gpu')
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        
        # メモリ不足・ポート競合クラッシュを徹底的に防ぐ
        options.add_argument('--remote-debugging-pipe') # 9222ポート競合を避けるパイプ通信
        options.add_argument(f'--crash-dumps-dir={unique_cache_dir}')
        
        # プロファイルとキャッシュを指定
        options.add_argument(f"--user-data-dir={unique_user_data_dir}")
        options.add_argument(f"--disk-cache-dir={unique_cache_dir}")

        options.binary_location = "/usr/local/bin/google-chrome"
        service = Service(executable_path="/usr/local/bin/chromedriver")

        # Selenium起動
        driver = webdriver.Chrome(service=service, options=options)

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
        # 1. ブラウザを安全に閉じる
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        
        # 2. 【重要】Cloud Runのディスク枯渇を防ぐため、使った一時フォルダを完全削除する
        for d in [unique_user_data_dir, unique_cache_dir]:
            if os.path.exists(d):
                try:
                    shutil.rmtree(d, ignore_errors=True)
                except Exception:
                    pass
