FROM python:3.11-slim-bookworm

WORKDIR /app

# 必要な apt パッケージとフォントなど
RUN apt-get update && apt-get install -y \
    libssl-dev \
    libffi-dev \
    python3-dev \
    cargo \
    wget \
    unzip \
    curl \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    poppler-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# --- 【変更箇所】 Chrome for Testing (137.0.7151.119) 本体のインストール ---
RUN wget -q -O /tmp/chrome.zip \
    https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.119/linux64/chrome-linux64.zip \
 && unzip /tmp/chrome.zip -d /opt/ \
 && ln -s /opt/chrome-linux64/chrome /usr/local/bin/google-chrome \
 && chmod +x /opt/chrome-linux64/chrome \
 && rm /tmp/chrome.zip

# --- 【変更箇所】 対応 ChromeDriver のインストール ---
RUN wget -q -O /tmp/chromedriver.zip \
    https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.119/linux64/chromedriver-linux64.zip \
 && unzip /tmp/chromedriver.zip -d /opt/ \
 && ln -s /opt/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
 && chmod +x /opt/chromedriver-linux64/chromedriver \
 && rm /tmp/chromedriver.zip

# Python ライブラリ関連
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app

CMD ["python", "main.py"]
