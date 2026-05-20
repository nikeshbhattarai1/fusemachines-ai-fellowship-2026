from openai import OpenAI
from config import Config


class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=Config.GROQ_API_KEY,
            base_url=Config.BASE_URL
        )
        self.model = Config.MODEL_NAME

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        """Centralized standard wrapper for Groq completions API endpoints."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content.strip()


llm_client = LLMClient()
