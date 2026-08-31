import json
import urllib.error
import urllib.request

from app.ai.base import AiGenerationError
from app.core.config import Settings


class GeminiClient:
    def __init__(self, settings: Settings):
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_model
        self._base_url = settings.gemini_base_url.rstrip("/")
        self._timeout = settings.gemini_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured:
            raise AiGenerationError("Gemini API Key가 설정되어 있지 않습니다.")

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
            },
        }
        request = urllib.request.Request(
            url=f"{self._base_url}/models/{self._model}:generateContent?key={self._api_key}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise AiGenerationError(f"Gemini API 요청 실패: {exc.code} {detail}") from exc
        except OSError as exc:
            raise AiGenerationError("Gemini API 연결에 실패했습니다.") from exc

        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise AiGenerationError("Gemini API 응답 형식이 예상과 다릅니다.") from exc
