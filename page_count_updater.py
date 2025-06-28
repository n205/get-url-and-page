import logging
import numpy as np
import requests
from pypdf import PdfReader
from io import BytesIO
from gspread_dataframe import get_as_dataframe, set_with_dataframe


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
    df.fillna('', inplace=True)

    updated = 0
    for idx, row in df.iterrows():
        url = row['URL']
        page = row['ページ数']
        if url and (page == '' or str(page).strip() == 'nan'):
            count = get_pdf_page_count(url)
            df.at[idx, 'ページ数'] = count
            logging.info(f'📄 ページ数取得: {url} → {count}')
            updated += 1

    if updated > 0:
        df.replace([np.nan, np.inf, -np.inf], '', inplace=True)
        worksheet.update(f'C2:C{len(df)+1}', [[v] for v in df['ページ数'].tolist()])
        logging.info(f'✅ {updated} 件のページ数を更新しました')
        return f'{updated} 件更新', 200
    else:
        logging.info('🔁 更新なし（空欄なし）')
        return '更新対象なし', 200
