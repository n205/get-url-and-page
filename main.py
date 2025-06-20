from flask import Flask
import requests
from pypdf import PdfReader
from io import BytesIO
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2 import service_account

app = Flask(__name__)

@app.route('/', methods=['GET'])
def process_pdf_links():
    # Google Sheets 設定
    SPREADSHEET_ID = 'あなたのスプレッドシートID'
    WORKSHEET_NAME = 'バリュー抽出'

    # 認証（サービスアカウント json を使う）
    creds = service_account.Credentials.from_service_account_file(
        'service_account.json',
        scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)
    worksheet = sh.worksheet(WORKSHEET_NAME)

    # 既存URL取得
    try:
        existing_df = get_as_dataframe(worksheet).dropna(subset=['URL'])
        processed_urls = set(existing_df['URL'].tolist())
    except:
        existing_df = pd.DataFrame(columns=['会社名', 'バリュー', 'ページ数', 'URL'])
        processed_urls = set()

    # JPX ESG PDFリンク取得
    url = 'https://jpx.esgdata.jp/app?分類=統合報告書'
    res = requests.get(url)
    hrefs = set()
    import re
    for match in re.findall(r'"(https://[^\"]+?\.pdf)"', res.text):
        if match not in processed_urls:
            hrefs.add(match)

    # ページ数取得
    new_rows = []
    for link in hrefs:
        try:
            res = requests.get(link, timeout=15)
            reader = PdfReader(BytesIO(res.content))
            pages = len(reader.pages)
        except Exception:
            pages = 0
        new_rows.append({
            '会社名': '',
            'バリュー': '',
            'ページ数': pages,
            'URL': link
        })

    # スプレッドシート保存
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        final_df = pd.concat([existing_df, new_df], ignore_index=True)
        worksheet.clear()
        set_with_dataframe(worksheet, final_df)

    return '✅ PDF情報を更新しました'

