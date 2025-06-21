from flask import Flask
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account
import logging

# Cloud Logging に出力するよう設定
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def main():
    logging.info('📥 リクエスト受信')
    return 'Cloud Run Function executed.', 200

if __name__ == '__main__':
    logging.info('🚀 アプリ起動')
    app.run(host='0.0.0.0', port=8080)
