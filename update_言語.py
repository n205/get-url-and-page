import logging
import os
from io import BytesIO
import requests
import warnings
from pypdf import PdfReader
from pdf2image import convert_from_bytes
import google.generativeai as genai
from gspread_dataframe import get_as_dataframe
import numpy as np
import pandas as pd

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
text_model = genai.GenerativeModel('gemini-2.5-flash')
image_model = genai.GenerativeModel('gemini-2.5-flash')

def detect_language_from_text(pdf_bytes):
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        all_text = ""

        # 最初の5ページ分のみ抽出
        for i in range(min(5, len(reader.pages))):
            t = reader.pages[i].extract_text() or ""
            all_text += t + "\n"

        if not all_text.strip():
            return "対象外"

        prompt = """
            以下のテキストが日本語中心かを判定してください。
            
            - 日本語 → 「日本語」
            - それ以外 → 「対象外」
            
            判定のみ1行で返してください。
        """

        response = text_model.generate_content([prompt, all_text])
        return response.text.strip()

    except Exception as e:
        logging.warning(f"Gemini言語判定エラー: {e}")
        return "対象外"


def update_言語T(worksheet):
    df = get_as_dataframe(worksheet)
    #df.fillna("", inplace=True)
    df = df.astype(object).fillna("")

    updated = 0

    for idx, row in df.iterrows():
        url = row["URL"]
        lang_T = row.get("言語T", "")
        page_count = row.get("ページ数", "")

        # URLなし or 既に判定済み → スキップ
        if not url or lang_T:
            continue

        # ページ数でフィルタ（15以下は対象外）
        try:
            if str(page_count).isdigit() and int(page_count) <= 15:
                df.at[idx, "言語T"] = "対象外"
                updated += 1
                logging.info(f"⏭️ 対象外（ページ数15以下）: {url}")
                continue
        except:
            pass

        # PDFダウンロードして言語判定
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)

            if r.status_code != 200:
                df.at[idx, "言語T"] = "対象外"
                updated += 1
                logging.info(f"⚠️ ダウンロード失敗: {url}")
                continue

            detected = detect_language_from_text(r.content)
            df.at[idx, "言語T"] = detected
            updated += 1
            logging.info(f"✅ 言語判定: {url} → {detected}")

        except Exception as e:
            df.at[idx, "言語T"] = "対象外"
            updated += 1
            logging.warning(f"❌ 言語判定エラー: {e} → {url}")

    # 書き戻し
    if updated > 0:
        col_idx = df.columns.get_loc("言語T")
        col_letter = chr(ord("A") + col_idx)

        worksheet.update(
            f"{col_letter}2:{col_letter}{len(df)+1}",
            [[v] for v in df["言語T"].tolist()],
        )

        logging.info(f"📝 {updated} 件の言語Tを更新しました")
        return f"{updated} 件更新", 200

    else:
        logging.info("🔁 言語T 更新なし")
        return "更新対象なし", 200

def detect_language_from_pdf_image(pdf_bytes):
    """PDFを画像化し、日本語判定を行う"""
    try:
        images = convert_from_bytes(
            pdf_bytes,
            dpi=200,
            first_page=1,
            last_page=5
        )

        response = image_model.generate_content([
            '''
            以下のテキストは統合報告書の最初の数ページです。
            このテキストの大部分が日本語かどうか判定してください。

            - 日本語の場合：「日本語」
            - 日本語以外の場合：「対象外」
            - 判定のみ1行で出力してください
            ''',
            *images
        ])

        return response.text.strip()

    except Exception as e:
        warnings.warn(f'Gemini画像処理失敗（言語G）: {e}')
        return '対象外'


# ============================
#  言語Gを更新するメイン処理
# ============================
def update_言語G(worksheet):
    df = get_as_dataframe(worksheet)
    #df.fillna('', inplace=True)
    df = df.astype(object).fillna("")

    update_count = 0

    for idx, row in df.iterrows():
        url = row['URL']
        lang_g = row.get('言語G', '')
        page_count = row['ページ数']

        # URLなし or すでに確定済ならスキップ
        if not url or lang_g in ['日本語', '対象外']:
            continue

        # ページ数少ないものは対象外
        if isinstance(page_count, (int, float)) and page_count <= 15:
            df.at[idx, '言語G'] = '対象外'
            update_count += 1
            logging.info(f'⏭️ ページ数少ないため対象外: {url}')
            continue

        detected_lang = '対象外'

        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/137.0.0.0 Safari/537.36'
                )
            }
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                detected_lang = detect_language_from_pdf_image(response.content)
            else:
                logging.warning(f'⚠️ ダウンロード失敗: {url} status={response.status_code}')

        except Exception as e:
            logging.warning(f'❌ 言語Gエラー → {e} → {url}')

        # 安全策：必ず「日本語」or「対象外」
        if detected_lang not in ['日本語', '対象外']:
            detected_lang = '対象外'

        df.at[idx, '言語G'] = detected_lang
        update_count += 1
        logging.info(f'🔄 言語G更新: {url} → {detected_lang}')

    # --- シート更新 ---
    if update_count > 0:
        df.replace([np.nan, np.inf, -np.inf], '', inplace=True)
        col_idx = df.columns.get_loc('言語G')
        col_letter = chr(ord('A') + col_idx)

        worksheet.update(
            f'{col_letter}2:{col_letter}{len(df)+1}',
            [[value] for value in df['言語G'].tolist()]
        )

        logging.info(f'📝 {update_count} 件の言語Gを更新しました')
        return f'{update_count} 件更新', 200
    else:
        logging.info('🔁 言語G更新なし')
        return '更新対象なし', 200
