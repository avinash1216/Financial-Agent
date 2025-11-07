# import pymysql
# from config import settings
# import models

# def init_db():
#     try:
#         # Connect to MySQL server
#         conn = pymysql.connect(
#             host=settings.DB_HOST,
#             port=int(settings.DB_PORT),
#             user=settings.DB_USER,
#             password=settings.DB_PASSWORD,
#             database=settings.DB_NAME
#         )
#         print("✅ Connection to MySQL server successful!")

#         cursor = conn.cursor()
#         conn.close()

#     except pymysql.Error as e:
#         print(f"❌ MySQL connection failed: {e}")

# if __name__ == "__main__":
#     init_db()


# ...existing code...
# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db():
    import app.models as models
    Base.metadata.create_all(bind=engine)


# ...existing code...