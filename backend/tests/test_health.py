"""/health는 DB 연결까지 확인한다 (무중단 배포 규칙)."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.api.health import DatabaseCheck
from app.config import Settings
from app.main import create_app


def test_health_ok_when_database_ok(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


def test_health_503_when_database_down(
    client_factory: Callable[..., TestClient], database_down: DatabaseCheck
) -> None:
    res = client_factory(database_check=database_down).get("/health")
    assert res.status_code == 503
    body = res.json()
    assert body["code"] == "DATABASE_UNAVAILABLE"
    assert body["request_id"] == res.headers["x-request-id"]


def test_app_starts_without_database_url_and_reports_unavailable() -> None:
    """DATABASE_URL이 없어도 앱은 뜨고, /health가 503으로 알려준다 (실제 lifespan 사용)."""
    app = create_app(Settings(_env_file=None, app_env="production"))
    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.get("/health")
    assert res.status_code == 503
    assert res.json()["code"] == "DATABASE_UNAVAILABLE"
    assert "detail" not in res.json()
