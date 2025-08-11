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

def update_page_counts(worksheet):
    df = get_as_dataframe(worksheet)

    # 「取得日」列がなければ追加
    if '取得日' not in df.columns:
        df['取得日'] = None

    updated = 0
    for idx, row in df.iterrows():
        url = row['URL']
        page = row['ページ数']

        # ページ数未入力の場合のみ取得
        if url and (pd.isna(page) or str(page).strip() == ''):
            count = get_pdf_page_count(url)
            df.at[idx, 'ページ数'] = count
            df.at[idx, '取得日'] = datetime.now().strftime('%Y-%m-%d')
            logging.info(f'📄 ページ数取得: {url} → {count}（取得日: {df.at[idx, "取得日"]}）')
            updated += 1

    if updated > 0:
        # NaN→None変換 & ページ数はint化
        df['ページ数'] = df['ページ数'].apply(lambda x: None if pd.isna(x) else int(x))

        # ページ数列の位置
        col_index_page = df.columns.get_loc('ページ数')
        col_letter_page = chr(ord('A') + col_index_page)

        # 取得日列の位置
        col_index_date = df.columns.get_loc('取得日')
        col_letter_date = chr(ord('A') + col_index_date)

        # ページ数更新
        worksheet.update(
            f'{col_letter_page}2:{col_letter_page}{len(df)+1}',
            [[v] for v in df['ページ数'].tolist()]
        )

        # 取得日更新
        worksheet.update(
            f'{col_letter_date}2:{col_letter_date}{len(df)+1}',
            [[v] for v in df['取得日'].tolist()]
        )

        logging.info(f'✅ {updated} 件のページ数と取得日を更新しました')
        return f'{updated} 件更新', 200
    else:
        logging.info('🔁 更新なし（空欄なし）')
        return '更新対象なし', 200
