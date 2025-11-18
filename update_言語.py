import logging
import pandas as pd
import requests
from datetime import datetime
from pypdf import PdfReader
from io import BytesIO
from gspread_dataframe import get_as_dataframe

def get_pdf_page_count(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        reader = PdfReader(BytesIO(response.content))
        if reader.is_encrypted:
            reader.decrypt('')
        return len(reader.pages)
    except Exception as e:
        logging.warning(f'⚠️ ページ数取得失敗: {url} 理由: {e}')
        return 0
