"""앱을 import하고 OpenAPI를 내보내는 데 DB 접속이나 환경변수가 필요 없어야 한다.

프론트 타입 생성(npm run gen:api)과 CI가 DB 없이 돌아가기 위한 조건이다.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

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


def test_import_does_not_create_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """import와 create_app만으로는 DB 풀을 만들지 않는다 (풀은 lifespan에서)."""
    import psycopg_pool

    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("DB pool created outside lifespan")

    monkeypatch.setattr(psycopg_pool, "AsyncConnectionPool", _forbidden)
    monkeypatch.setenv("DATABASE_URL", UNREACHABLE_DB)

    from app.config import Settings
    from app.main import create_app

    app = create_app(Settings(_env_file=None))
    assert "/health" in app.openapi()["paths"]


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
