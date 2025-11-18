import logging
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import numpy as np


def sheet_read():
    SPREADSHEET_ID = '18Sb4CcAE5JPFeufHG97tLZz9Uj_TvSGklVQQhoFF28w'
    WORKSHEET_NAME = 'バリュー抽出'

    try:
        creds = service_account.Credentials.from_service_account_file(
            '/secrets/service-account-json',
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(WORKSHEET_NAME)

        existing_df = get_as_dataframe(worksheet).dropna(subset=['URL'])
        processed_urls = set(existing_df['URL'].tolist())

        logging.info(f'✅ 取得済URL数: {len(processed_urls)}')
        return worksheet, existing_df, processed_urls

    except Exception as e:
        import traceback
        logging.error('❌ エラー発生:\n' + traceback.format_exc())
        return f'エラー: {e}', 500



def append_new_pdf_links(worksheet, existing_df, processed_urls):
    try:
        # Selenium起動
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)

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

        driver.quit()

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
