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

    jwt_secret: str = "change-me"
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 7
    hmac_secret: str = "change-me"

    nvidia_api_key: str = ""
    default_chat_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    default_vision_model: str = "meta/llama-3.2-90b-vision-instruct"
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

    frontend_url: str = "http://localhost:5173"
    cors_allowed_origins: str = "http://localhost:5173"

    upload_dir: str = "data/uploads"
    max_upload_size_mb: int = 25


settings = Settings()
