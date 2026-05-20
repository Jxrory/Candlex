from pydantic_settings import BaseSettings
from typing import ClassVar


class Settings(BaseSettings):
    db_dsn: str = "postgresql://user:password@127.0.0.1:5432/candlex"
    db_min_connections: int = 2
    db_max_connections: int = 10

    cache_ttl_today_seconds: int = 60
    cache_ttl_recent_days: int = 5
    cache_ttl_recent_seconds: int = 300
    source_priority: list[str] = ["sina", "tencent", "eastmoney"]

    dividend_sync_time: str = "08:30"
    dividend_sync_symbols: list[str] = []

    model_config: ClassVar[dict] = {"env_prefix": "CANDLEX_", "env_file": ".env"}


settings = Settings()
