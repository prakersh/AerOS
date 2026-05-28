from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AEROS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 4040
    debug: bool = False

    database_url: str = "sqlite:///data/aeros.db"

    jwt_secret: str = "change-me"  # noqa: S105
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 7
    hmac_secret: str = "change-me"  # noqa: S105

    mimo_api_key: str = ""
    mimo_base_url: str = "https://token-plan-sgp.xiaomimimo.com/v1"
    default_chat_model: str = "mimo-v2.5"
    default_vision_model: str = "mimo-v2.5"
    nvidia_api_key: str = ""
    default_embed_model: str = "nvidia/nv-embed-v1"

    groq_api_key: str = ""

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    smtp_from_address: str = "procurement@aeros.local"

    imap_host: str = "localhost"
    imap_port: int = 1143
    imap_username: str = ""
    imap_password: str = ""
    imap_poll_interval_sec: int = 30

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    show_demo_credentials: bool = True

    frontend_url: str = "http://localhost:5173"
    cors_allowed_origins: str = "http://localhost:5173"

    upload_dir: str = "data/uploads"
    max_upload_size_mb: int = 25


settings = Settings()
