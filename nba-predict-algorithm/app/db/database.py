"""
数据库连接配置
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass
