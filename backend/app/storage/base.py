from typing import Any, Protocol


class AppStore(Protocol):
    def create_chat_session(self, session_id: str) -> None:
        ...

    def add_chat_message(self, session_id: str, message: Any) -> None:
        ...

    def get_chat_history(self, session_id: str, limit: int = 30) -> list[Any]:
        ...

    def save_feedback(
        self,
        target: str,
        rating: str,
        capability: str | None,
        prompt: str | None,
        result_preview: str | None,
    ) -> int:
        ...
