import re
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")

# Cloudflare Pages의 pages.dev 하위 도메인(예: codemap-bq7): 소문자, 숫자, 하이픈.
# 프로젝트 이름과 다를 수 있으니 실제 배정된 주소의 앞부분을 쓴다.
# 점이 없어야 정규식이 다른 프로젝트 주소와 섞이지 않는다.
_PAGES_PROJECT_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,56}[a-z0-9])?$")


class Settings(BaseSettings):
    """환경변수 설정. 모든 값에 기본값이 있어 import만으로는 아무것도 요구하지 않는다."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 기본값은 production이다. APP_ENV를 빠뜨려도 에러 응답에 detail이 새지 않는다.
    app_env: Literal["development", "production"] = "production"
    database_url: str | None = None
    pages_project_name: str | None = None

    @field_validator("pages_project_name")
    @classmethod
    def _must_be_pages_project_name(cls, value: str | None) -> str | None:
        if value is not None and not _PAGES_PROJECT_NAME.fullmatch(value):
            raise ValueError(
                "PAGES_PROJECT_NAME은 pages.dev 하위 도메인(예: codemap-bq7)이어야 합니다"
            )
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
