from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.health import DatabaseCheck, get_database_check
from app.config import Settings
from app.domain.errors import AppError
from app.main import create_app

ENV_VARS = ("APP_ENV", "DATABASE_URL", "PAGES_PROJECT_NAME")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """개발자 컴퓨터의 환경변수나 .env가 테스트 결과를 바꾸지 않게 한다."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


async def _database_ok() -> None:
    return None


async def _database_down() -> None:
    raise AppError(
        status_code=503,
        code="DATABASE_UNAVAILABLE",
        message="데이터베이스에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.",
        detail="fake: connection refused",
    )


def make_client(
    settings: Settings | None = None,
    database_check: DatabaseCheck = _database_ok,
) -> TestClient:
    app = create_app(settings or Settings(_env_file=None))
    app.dependency_overrides[get_database_check] = lambda: database_check
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client_factory() -> Callable[..., TestClient]:
    return make_client


@pytest.fixture
def client() -> Iterator[TestClient]:
    yield make_client()


@pytest.fixture
def database_down() -> DatabaseCheck:
    return _database_down
