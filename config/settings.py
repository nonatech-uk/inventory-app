from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Postgres — stuff database
    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "stuff"
    db_user: str = "stuff"
    db_password: str = ""
    db_sslmode: str = "prefer"

    # Cross-DB (finance — for Amazon order lookups)
    finance_db_name: str = "finance"
    finance_db_user: str = "finance"
    finance_db_password: str = ""

    # External services
    immich_url: str = "http://localhost:2283"
    immich_public_url: str = "https://pix.mees.st"
    immich_api_key: str = ""
    immich_tag_api_key: str = ""  # key with tag.create + tag.asset perms (falls back to immich_api_key)
    paperless_url: str = "http://localhost:8000"
    paperless_api_token: str = ""
    tmdb_api_key: str = ""

    # eBay API
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_refresh_token: str = ""
    ebay_ru_name: str = ""
    ebay_site_id: str = "3"  # UK
    ebay_verification_token: str = ""

    # Storage
    image_storage_path: str = "/app/data/images"

    # Pipeline ingest
    pipeline_secret: str = ""

    # Auth
    auth_enabled: bool = True
    dev_user_email: str = "stu@mees.st"
    cors_origins: list[str] = [
        "https://stuff.mees.st",
        "http://localhost:5173",
    ]

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8300
    db_pool_min: int = 2
    db_pool_max: int = 5

    # Usage tracking
    usage_dsn: str = ""

    model_config = {
        "env_file": str(Path(__file__).resolve().parent / ".env"),
        "env_file_encoding": "utf-8",
    }

    @property
    def dsn(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password} sslmode={self.db_sslmode}"
        )

    def cross_dsn(self, db_name: str, db_user: str, db_password: str) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={db_name} "
            f"user={db_user} password={db_password} sslmode={self.db_sslmode}"
        )


settings = Settings()
