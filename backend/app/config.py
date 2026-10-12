import re
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")

# Cloudflare Pages 운영 주소만 받는다. 미리보기(<hash>.<project>.pages.dev)는 허용하지 않는다.
_PAGES_ORIGIN = re.compile(r"^https://[a-z0-9-]+\.pages\.dev$")


class Settings(BaseSettings):
    """환경변수 설정. 모든 값에 기본값이 있어 import만으로는 아무것도 요구하지 않는다."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "production"] = "development"
    database_url: str | None = None
    frontend_origin: str | None = None

    @field_validator("frontend_origin")
    @classmethod
    def _must_be_pages_origin(cls, value: str | None) -> str | None:
        if value is not None and not _PAGES_ORIGIN.fullmatch(value):
            raise ValueError("FRONTEND_ORIGIN은 https://<프로젝트>.pages.dev 형식이어야 합니다")
        return value

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def cors_origins(self) -> list[str]:
        origins = list(LOCAL_DEV_ORIGINS)
        if self.frontend_origin:
            origins.append(self.frontend_origin)
        return origins
