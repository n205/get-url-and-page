import logging
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account

import uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import numpy as np


def update_pdf_links(worksheet, existing_df, processed_urls):
    driver = None
    try:
        # --- Selenium起動オプションの設定 ---
        options = Options()
        options.add_argument('--headless=new')  # 最新のヘッドレスモード
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')

        # 【重要】Cloud Run上でのプロファイル競合と読み取り専用エラーを回避
        unique_user_data_dir = f"/tmp/chrome_user_data_{uuid.uuid4()}"
        options.add_argument(f"--user-data-dir={unique_user_data_dir}")
        options.add_argument("--disk-cache-dir=/tmp/chrome_cache")

        # 【重要】Dockerfileで配置したChrome本体とDriverを明示的に指定
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
        # エラー発生時でも確実にブラウザプロセスを終了させる
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
