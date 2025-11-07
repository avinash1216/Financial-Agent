# app/extractors/pdf_loader.py
from langchain_community.document_loaders import PyPDFLoader
from app.config import settings

def load_pdf_text(path: str) -> str:
    loader = PyPDFLoader(path)
    docs = loader.load()
    return "\n\n".join([d.page_content for d in docs])