from pathlib import Path

from mees_shared.settings import BaseAppSettings


class Settings(BaseAppSettings):
    db_name: str = "stuff"
    db_user: str = "stuff"
    db_sslmode: str = "prefer"
    api_port: int = 8300
    db_pool_max: int = 5

    cors_origins: list[str] = [
        "https://stuff.mees.st",
        "http://localhost:5173",
    ]

    # External services
    immich_url: str = "http://localhost:2283"
    immich_public_url: str = "https://pix.mees.st"
    immich_api_key: str = ""
    immich_tag_api_key: str = ""
    paperless_url: str = "http://localhost:8000"
    paperless_api_token: str = ""
    tmdb_api_key: str = ""

    # eBay API
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_refresh_token: str = ""
    ebay_ru_name: str = ""
    ebay_site_id: str = "3"
    ebay_verification_token: str = ""

    # Healthcheck UUIDs
    hc_ebay_sync: str = ""
    hc_immich_tag_sync: str = ""

    # Storage
    image_storage_path: str = "/app/data/images"

    # Pipeline ingest
    pipeline_secret: str = ""

    model_config = {
        "env_file": str(Path(__file__).resolve().parent / ".env"),
        "env_file_encoding": "utf-8",
    }

settings = Settings()
