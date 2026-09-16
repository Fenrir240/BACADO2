import os

from google import genai


class GeminiProvider:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        model = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")

        if not api_key:
            raise RuntimeError(
                "Lipsește GOOGLE_API_KEY din .env. Adaugă cheia API pentru Gemini."
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_text(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        return response.text or ""

    def generate_json(self, prompt: str, response_schema: dict | None = None) -> str:
        """Request machine-readable JSON instead of relying on prompt wording."""
        config = {"response_mime_type": "application/json"}
        if response_schema is not None:
            config["response_schema"] = response_schema

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        return response.text or ""
