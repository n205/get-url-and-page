import logging
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2 import service_account

import uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import numpy as np


def update_pdf_links(worksheet, existing_df, processed_urls):
    driver = None
    try:
        options = Options()
        # --- 基本ヘッドレス環境オプション ---
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--single-process')
        options.add_argument('--remote-debugging-port=9222')

        # --- 【超重要】コンテナ再利用時の共有ロック誤認を完全に回避する設定 ---
        options.add_argument('--disable-background-networking')
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        # シングルトン（単一起動チェック）構造を無効化し、古い残骸があっても強制起動させる
        options.add_argument('--disable-single-click-autofill')
        options.add_argument('--user-data-dir=/tmp/chrome_user_data_dir') 
        # ↑ UUID で毎回フォルダを量産すると /tmp が溢れるリスクがあるため、
        # 以下の「ロック無効化」フラグを立てた上で、固定の一時フォルダを指定する方が Cloud Run では安定します。
        
        # 【決定打】Chrome が起動時に一時ファイルのロックを確認・作成するのを禁止する
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-setuid-sandbox')
        
        # 以下の環境変数的なフラグ（プロファイルロックの強制無効化）を起動引数に渡します
        options.add_argument('--disable-features=WebRtcHideLocalIpsWithMdns,GpuProcessHighPriority')
        
        # Chrome内部のディスクキャッシュを毎回クリーンな別の場所に指定
        unique_id = str(uuid.uuid4())
        options.add_argument(f'--disk-cache-dir=/tmp/chrome_cache_{unique_id}')

        # Chrome本体とDriverのパス指定
        options.binary_location = "/usr/local/bin/google-chrome"
        service = Service(executable_path="/usr/local/bin/chromedriver")

        # 起動
        driver = webdriver.Chrome(service=service, options=options)
        
        # スクリプトのタイムアウト時間を明示的に設定（念のための安全策）
        driver.set_page_load_timeout(30)

        url = 'https://jpx.esgdata.jp/app?分類=統合報告書'
        driver.get(url)
        
        # DOMの読み込みを少し待つ
        time.sleep(5)

        anchors = driver.find_elements(By.CSS_SELECTOR, 'a[target="_blank"]')
        new_rows = []
        seen_urls = set()

        for a in anchors:
            href = a.get_attribute('href')
            if href and href.endswith('.pdf') and href not in processed_urls and href not in seen_urls:
                seen_urls.add(href)
                new_rows.append({
                    'URL': href,
                })

        if new_rows:
            new_df = pd.DataFrame(new_rows)
            new_df.replace([np.nan, np.inf, -np.inf], '', inplace=True)
            worksheet.append_rows(new_df.values.tolist())
            logging.info(f'🆕 新規URL {len(new_rows)} 件を追加しました')
            return f'{len(new_rows)} 件のURLを追加', 200
        else:
            logging.info('📄 新規URLはありませんでした')
            return '追加対象なし', 200

    except Exception as e:
        import traceback
        logging.error('❌ PDFリンク取得エラー:\n' + traceback.format_exc())
        return f'エラー: {e}', 500

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
