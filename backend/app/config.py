import re
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")

# Cloudflare Pages 프로젝트 이름: 소문자, 숫자, 하이픈.
# 점이 없어야 정규식이 다른 프로젝트 주소와 섞이지 않는다.
_PAGES_PROJECT_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,56}[a-z0-9])?$")


class Settings(BaseSettings):
    """환경변수 설정. 모든 값에 기본값이 있어 import만으로는 아무것도 요구하지 않는다."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "production"] = "development"
    database_url: str | None = None
    pages_project_name: str | None = None

    @field_validator("pages_project_name")
    @classmethod
    def _must_be_pages_project_name(cls, value: str | None) -> str | None:
        if value is not None and not _PAGES_PROJECT_NAME.fullmatch(value):
            raise ValueError("PAGES_PROJECT_NAME은 Cloudflare Pages 프로젝트 이름이어야 합니다")
        return value

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def cors_origins(self) -> list[str]:
        return list(LOCAL_DEV_ORIGINS)

    @property
    def cors_origin_regex(self) -> str | None:
        """우리 Pages 프로젝트의 운영 주소와 미리보기 주소(<무엇이든>.<프로젝트>.pages.dev)."""
        if self.pages_project_name is None:
            return None
        project = re.escape(self.pages_project_name)
        return rf"^https://(?:[a-z0-9-]+\.)?{project}\.pages\.dev$"
