import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    BASE_URL = os.getenv("BASE_URL", "https://api.groq.com/openai/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres_secure_pass@postgres_db:5432/classicmodels")
