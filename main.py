from flask import Flask
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account
import logging

from read_sheet import read_sheet
from update_pdf_link import update_pdf_links
from update_page_count import update_page_counts
from update_言語 import update_言語T
from update_言語 import update_言語G


# Cloud Logging に出力するよう設定
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def main():
    logging.info('📥 リクエスト受信')

    # スプレッドシート読込
    worksheet, existing_df, processed_urls = read_sheet()

    # pdfリンク追加
    update_pdf_links(worksheet, existing_df, processed_urls)

    # ページ数追加
    update_page_counts(worksheet)

    update_言語T(worksheet)
    update_言語G(worksheet)
    
    return 'Cloud Run Function executed.', 200


if __name__ == '__main__':
    logging.info('🚀 アプリ起動')
    app.run(host='0.0.0.0', port=8080)
