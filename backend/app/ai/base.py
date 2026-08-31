from typing import Protocol


class AiGenerationError(RuntimeError):
    pass


class AiClient(Protocol):
    @property
    def is_configured(self) -> bool:
        ...

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        ...
