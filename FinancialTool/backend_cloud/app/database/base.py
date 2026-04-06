from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator
from backend_cloud.config.settings import BASE_DB_PATH

# Tạm thời dùng SQLite cho dễ dev. Lên Production thay bằng chuỗi PostgreSQL:
# DATABASE_URL = "postgresql://user:password@localhost:5432/core_db"
DATABASE_URL = f"sqlite:///{BASE_DB_PATH}"

# connect_args={"check_same_thread": False} chỉ cần cho SQLite trong FastAPI
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency dùng để tiêm (inject) vào các route của FastAPI
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()