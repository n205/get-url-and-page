import logging
from pypdf import PdfReader
from io import BytesIO
import requests
from gspread_dataframe import get_as_dataframe
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
text_model = genai.GenerativeModel("gemini-2.0-flash")

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


def update_language_T(worksheet):
    df = get_as_dataframe(worksheet)
    df.fillna("", inplace=True)

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
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)

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
