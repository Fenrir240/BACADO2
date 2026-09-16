import os

from dotenv import load_dotenv


load_dotenv()

_provider_instance = None


def get_ai_provider():
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = os.getenv("AI_PROVIDER", "openrouter").lower()

    if provider_name in {"openrouter", "qwen"}:
        from services.openrouter_provider import OpenRouterProvider

        _provider_instance = OpenRouterProvider()
        return _provider_instance

    if provider_name == "gemini":
        from services.gemini_provider import GeminiProvider

        _provider_instance = GeminiProvider()
        return _provider_instance

    if provider_name == "mock":
        from services.mock_provider import MockProvider

        _provider_instance = MockProvider()
        return _provider_instance

    raise RuntimeError(f"Provider AI necunoscut: {provider_name}")
