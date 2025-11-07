import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


class Settings:
    # SQL Server connection details
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_USER: str = os.getenv("DB_USER", "sa")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "your_password")
    DB_NAME: str = os.getenv("DB_NAME", "your_database")

    # Optional: SQLAlchemy fallback connection string
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/payslips.db")

    # OpenAI API key
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

    # Folder for PDF files
    PDF_FOLDER: str = os.getenv("PDF_FOLDER", "./payslips_pdf")

    # Logging level
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()