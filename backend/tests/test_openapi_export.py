"""앱을 import하고 OpenAPI를 내보내는 데 DB 접속이나 환경변수가 필요 없어야 한다.

프론트 타입 생성(npm run gen:api)과 CI가 DB 없이 돌아가기 위한 조건이다.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[1]

# 접속을 시도하면 즉시 실패하는 주소. import 중에 접속하면 내보내기가 실패하거나 멈춘다.
UNREACHABLE_DB = "postgresql://nobody:nothing@127.0.0.1:1/none?connect_timeout=1"


def _minimal_env(**extra: str) -> dict[str, str]:
    env = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp")}
    env.update(extra)
    return env


def _export(tmp_path: Path, env: dict[str, str]) -> dict[str, object]:
    out = tmp_path / "openapi.json"
    subprocess.run(
        [sys.executable, "-m", "scripts.export_openapi", str(out)],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
        timeout=30,
    )
    result: dict[str, object] = json.loads(out.read_text(encoding="utf-8"))
    return result


@pytest.mark.parametrize(
    "env",
    [
        pytest.param(_minimal_env(), id="no-env-vars"),
        pytest.param(_minimal_env(DATABASE_URL=UNREACHABLE_DB), id="unreachable-db"),
    ],
)
def test_export_needs_no_database_or_env(tmp_path: Path, env: dict[str, str]) -> None:
    spec = _export(tmp_path, env)
    assert "/health" in spec["paths"]  # type: ignore[operator]


class _PoolSpy:
    """AsyncConnectionPool 대신 들어가 생성 횟수만 센다."""

    created = 0

    def __init__(self, *args: object, **kwargs: object) -> None:
        type(self).created += 1

    async def open(self, wait: bool = True) -> None:
        return None

    async def close(self) -> None:
        return None


@pytest.fixture
def pool_spy(monkeypatch: pytest.MonkeyPatch) -> type[_PoolSpy]:
    from app.infrastructure.persistence import db

    _PoolSpy.created = 0
    monkeypatch.setattr(db, "AsyncConnectionPool", _PoolSpy)
    return _PoolSpy


def test_create_app_and_openapi_do_not_create_pool(pool_spy: type[_PoolSpy]) -> None:
    """create_app과 OpenAPI 생성만으로는 DB 풀을 만들지 않는다."""
    app = create_app(Settings(_env_file=None, database_url=UNREACHABLE_DB))
    assert "/health" in app.openapi()["paths"]
    assert pool_spy.created == 0


def test_pool_is_created_at_lifespan_start(pool_spy: type[_PoolSpy]) -> None:
    """풀은 앱이 시작될 때(lifespan) 만들어진다.

    위 테스트의 가짜 풀이 실제로 끼워졌음도 함께 보여준다.
    """
    app = create_app(Settings(_env_file=None, database_url=UNREACHABLE_DB))
    with TestClient(app):
        assert pool_spy.created == 1


def test_error_response_schema_is_published(tmp_path: Path) -> None:
    spec = _export(tmp_path, _minimal_env())
    schemas = spec["components"]["schemas"]  # type: ignore[index]
    error = schemas["ErrorResponse"]
    assert set(error["required"]) == {"code", "message", "request_id"}
    assert "detail" in error["properties"]
    assert "HTTPValidationError" not in schemas


def test_export_is_deterministic(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    _export(tmp_path / "a", _minimal_env())
    _export(tmp_path / "b", _minimal_env())
    assert (tmp_path / "a" / "openapi.json").read_bytes() == (
        tmp_path / "b" / "openapi.json"
    ).read_bytes()
