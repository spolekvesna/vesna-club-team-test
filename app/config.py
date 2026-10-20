from __future__ import annotations
import os
from dataclasses import dataclass


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}

@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    secret: str = os.getenv("APP_SECRET", "dev-only-change-me")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./runtime/vesna_club.db")
    allow_local_login: bool = _bool("ALLOW_LOCAL_LOGIN", os.getenv("APP_ENV", "development") != "production")
    base_url: str = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_allowed_domain: str = os.getenv("GOOGLE_ALLOWED_DOMAIN", "spolekvesna.cz")
    bootstrap_admin_email: str = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "")
    bootstrap_admin_name: str = os.getenv("BOOTSTRAP_ADMIN_NAME", "První správce")
    allowed_hosts_raw: str = os.getenv("ALLOWED_HOSTS", "")
    backup_dir: str = os.getenv("BACKUP_DIR", "./runtime/backups")
    backup_retention_days: int = int(os.getenv("BACKUP_RETENTION_DAYS", "35"))
    backup_s3_bucket: str = os.getenv("BACKUP_S3_BUCKET", "")
    backup_s3_prefix: str = os.getenv("BACKUP_S3_PREFIX", "vesna-club")
    backup_s3_endpoint: str = os.getenv("BACKUP_S3_ENDPOINT", "")
    backup_s3_region: str = os.getenv("BACKUP_S3_REGION", "")
    backup_s3_sse: str = os.getenv("BACKUP_S3_SSE", "AES256")
    restore_test_database_url: str = os.getenv("RESTORE_TEST_DATABASE_URL", "")
    ka31_32_limit_minutes: int = int(os.getenv("KA31_32_LIMIT_MINUTES", "600"))
    ka33_limit_minutes: int = int(os.getenv("KA33_LIMIT_MINUTES", "600"))


    @property
    def sqlalchemy_database_url(self) -> str:
        # Render exposes PostgreSQL URLs as postgresql://. This project uses psycopg 3.
        if self.database_url.startswith("postgresql://"):
            return "postgresql+psycopg://" + self.database_url[len("postgresql://"):]
        return self.database_url

    @property
    def allowed_hosts(self) -> list[str]:
        return [x.strip() for x in self.allowed_hosts_raw.split(",") if x.strip()]

settings = Settings()
