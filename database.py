"""
データベース設定

SQLAlchemyを使用したPostgreSQLデータベースの接続設定
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# データベースURL（環境変数またはデフォルト値）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/bento_db"
)

# SQLAlchemyエンジンを作成
engine = create_engine(DATABASE_URL)

# セッションクラスを作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ベースクラスを作成
Base = declarative_base()


def get_db():
    """
    データベースセッションを取得するジェネレータ
    FastAPIの依存関数として使用
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()