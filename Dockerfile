FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# entrypoint.shを実行可能にする
RUN chmod +x entrypoint.sh

# ポート8000を開放
EXPOSE 8000

# アプリケーションを起動
CMD ["bash", "entrypoint.sh"]