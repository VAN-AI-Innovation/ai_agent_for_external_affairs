import sqlite3
from pathlib import Path
from threading import Lock

from app.agents.chat_assistant import ChatMessage
from app.core.config import ROOT_DIR


class SQLiteStore:
    def __init__(self, database_url: str):
        self._db_path = self._resolve_path(database_url)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._initialize()

    def create_chat_session(self, session_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO chat_sessions (id)
                VALUES (?)
                """,
                (session_id,),
            )

    def add_chat_message(self, session_id: str, message: ChatMessage) -> None:
        self.create_chat_session(session_id)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_messages (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, message.role, message.content, message.created_at),
            )

    def get_chat_history(self, session_id: str, limit: int = 30) -> list[ChatMessage]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()

        return [
            ChatMessage(role=row["role"], content=row["content"], created_at=row["created_at"])
            for row in reversed(rows)
        ]

    def save_feedback(
        self,
        target: str,
        rating: str,
        capability: str | None,
        prompt: str | None,
        result_preview: str | None,
    ) -> int:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO feedback_events (target, rating, capability, prompt, result_preview)
                VALUES (?, ?, ?, ?, ?)
                """,
                (target, rating, capability, prompt, result_preview),
            )
            row = connection.execute("SELECT COUNT(*) AS count FROM feedback_events").fetchone()

        return int(row["count"])

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL DEFAULT (datetime('now'))
                    );

                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
                    );

                    CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id
                    ON chat_messages(session_id, id);

                    CREATE TABLE IF NOT EXISTS feedback_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        target TEXT NOT NULL,
                        rating TEXT NOT NULL,
                        capability TEXT,
                        prompt TEXT,
                        result_preview TEXT,
                        created_at TEXT NOT NULL DEFAULT (datetime('now'))
                    );
                    """
                )

    def _resolve_path(self, database_url: str) -> Path:
        if database_url.startswith("sqlite:///"):
            raw_path = database_url.removeprefix("sqlite:///")
        else:
            raw_path = database_url

        path = Path(raw_path)
        if not path.is_absolute():
            path = ROOT_DIR / path

        return path
