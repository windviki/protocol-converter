from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库配置
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///protocol_converter.db')

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv('DATABASE_ECHO', 'false').lower() == 'true'
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session():
    """获取数据库会话的上下文管理器"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def init_database():
    """初始化数据库"""
    from models.models import Base
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成")