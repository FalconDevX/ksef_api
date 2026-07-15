from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    ksef_token: str
    ksef_nip: str
    ksef_base_url: str
    database_url: str
    pdf_service_url: str = "http://ksef-pdf:8080"
    ksef_qr_base_url: str = "https://qr-test.ksef.mf.gov.pl"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings.model_validate({})
