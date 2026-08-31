from app.core.config import Settings
from app.storage.sqlite_store import SQLiteStore


def create_store(settings: Settings) -> SQLiteStore:
    if settings.database_url.startswith("sqlite:///") or settings.database_url.endswith(".db"):
        return SQLiteStore(settings.database_url)

    raise ValueError("현재는 sqlite:/// 형식의 DATABASE_URL을 지원합니다.")
