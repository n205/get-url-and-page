from flask import Flask
import logging

# Cloud Logging に出力するよう設定
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def main():
    logging.info('📥 リクエストを受け取りました')
    return 'Cloud Run Function executed.', 200

if __name__ == '__main__':
    logging.info('🚀 アプリを起動します')
    app.run(host='0.0.0.0', port=8080)
