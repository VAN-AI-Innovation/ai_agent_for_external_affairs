from app.ai.base import AiClient
from app.ai.gemini_client import GeminiClient
from app.ai.local_qwen import LocalQwenClient
from app.ai.openai_client import OpenAIClient
from app.core.config import Settings


def create_ai_client(settings: Settings) -> AiClient:
    provider = settings.ai_provider.lower().strip()

    if provider == "openai":
        return OpenAIClient(settings)
    if provider == "gemini":
        return GeminiClient(settings)
    if provider == "qwen":
        return LocalQwenClient(settings)
    if provider != "auto":
        raise ValueError("AI_PROVIDER는 auto, openai, gemini, qwen 중 하나여야 합니다.")

    if settings.openai_api_key:
        return OpenAIClient(settings)
    if settings.gemini_api_key:
        return GeminiClient(settings)

    return LocalQwenClient(settings)
