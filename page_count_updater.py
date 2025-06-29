import logging
import numpy as np
import pandas as pd
import requests
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

    updated = 0
    for idx, row in df.iterrows():
        url = row['URL']
        page = row['ページ数']

        # 未入力判定（NaNまたはNone）
        if url and (pd.isna(page) or str(page).strip() == ''):
            count = get_pdf_page_count(url)
            df.at[idx, 'ページ数'] = count
            logging.info(f'📄 ページ数取得: {url} → {count}')
            updated += 1

    if updated > 0:
        # 書き込み用にNaN→Noneへ変換
        df['ページ数'] = df['ページ数'].apply(lambda x: None if pd.isna(x) else int(x))

        worksheet.update(
            f'C2:C{len(df)+1}',
            [[v] for v in df['ページ数'].tolist()]
        )
        logging.info(f'✅ {updated} 件のページ数を更新しました')
        return f'{updated} 件更新', 200
    else:
        logging.info('🔁 更新なし（空欄なし）')
        return '更新対象なし', 200
