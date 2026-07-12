import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "gemma2-9b-it")
GROQ_MODEL_LARGE = os.getenv("GROQ_MODEL_LARGE", "llama-3.3-70b-versatile")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crm_hcp.db")
