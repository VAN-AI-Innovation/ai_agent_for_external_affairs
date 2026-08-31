import json
import urllib.error
import urllib.request

from app.ai.base import AiGenerationError
from app.core.config import Settings


class OpenAIClient:
    def __init__(self, settings: Settings):
        self._api_key = settings.openai_api_key
        self._model = settings.openai_model
        self._base_url = settings.openai_base_url.rstrip("/")
        self._timeout = settings.openai_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured:
            raise AiGenerationError("OpenAI API Key가 설정되어 있지 않습니다.")

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        }
        request = urllib.request.Request(
            url=f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise AiGenerationError(f"OpenAI API 요청 실패: {exc.code} {detail}") from exc
        except OSError as exc:
            raise AiGenerationError("OpenAI API 연결에 실패했습니다.") from exc

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise AiGenerationError("OpenAI API 응답 형식이 예상과 다릅니다.") from exc
