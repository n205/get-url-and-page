import logging
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account


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
        logging.info(1)
        gc = gspread.authorize(creds)
        logging.info(2)
        sh = gc.open_by_key(SPREADSHEET_ID)
        logging.info(3)
        worksheet = sh.worksheet(WORKSHEET_NAME)

        existing_df = get_as_dataframe(worksheet).dropna(subset=['URL'])
        processed_urls = set(existing_df['URL'].tolist())

        logging.info(f'✅ 取得済URL数: {len(processed_urls)}')
        return f'取得済URL数: {len(processed_urls)}', 200

    except Exception as e:
        logging.error(f'❌ エラー: {e}')
        return f'エラー: {e}', 500
