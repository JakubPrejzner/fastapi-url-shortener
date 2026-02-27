from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    api_host: str = "0.0.0.0"
    api_port: int = 9000
    short_url_max_len: int = 6
    base_url: str = "http://localhost:9000"
    log_format: str = "text"
    log_level: str = "INFO"
    rate_limit_enabled: bool = True
    rate_limit_max_requests: int = 60
    rate_limit_window_seconds: int = 60


settings = Settings()
