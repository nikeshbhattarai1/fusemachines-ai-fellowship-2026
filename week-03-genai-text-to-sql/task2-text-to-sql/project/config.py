import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME", "llama3-70b-8192")
    BASE_URL = os.getenv("BASE_URL", "https://api.groq.com/openai/v1")
