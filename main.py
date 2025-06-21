from flask import Flask

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def hello():
    print('📥 リクエストを受け取りました')
    return 'Cloud Run Function executed.', 2000

if __name__ == '__main__':
    print('🚀 アプリを起動します')
    app.run(host='0.0.0.0', port=8080)
