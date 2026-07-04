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
        # --- ヘッドレス環境のフル安定化オプション ---
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')  # /dev/shm の使用を避ける
        options.add_argument('--disable-gpu')
        options.add_argument('--single-process')        # 単一プロセスモードでメモリ節約
        options.add_argument('--remote-debugging-port=9222')

        # --- 【追加】重複起動・メモリ不足時のクラッシュを徹底防御するオプション ---
        options.add_argument('--disable-extensions')       # 拡張機能を無効化
        options.add_argument('--blink-settings=imagesEnabled=false')  # 画像の読み込みを無効化（超軽量化）
        options.add_argument('--disable-features=VizDisplayCompositor') # レンダリングの軽量化
        
        # ページ読み込み戦略を「eager（DOM確定時点で次の処理へ）」にしてタイムアウトを防ぐ
        options.page_load_strategy = 'eager'

        # 完全一意の一時ディレクトリ設定
        unique_id = str(uuid.uuid4())
        options.add_argument(f'--user-data-dir=/tmp/chrome_data_{unique_id}')
        options.add_argument(f'--data-path=/tmp/chrome_data_path_{unique_id}')
        options.add_argument(f'--disk-cache-dir=/tmp/chrome_cache_{unique_id}')

        options.binary_location = "/usr/local/bin/google-chrome"
        service = Service(executable_path="/usr/local/bin/chromedriver")

        # ブラウザ起動（ここでタイムアウトが発生しなくなります）
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
