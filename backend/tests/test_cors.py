"""CORS는 우리 Cloudflare Pages 프로젝트(운영·미리보기)와 로컬 개발 주소만 허용한다."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import LOCAL_DEV_ORIGINS, Settings

PROJECT = "codemap"


def _preflight(client: TestClient, origin: str) -> str | None:
    res = client.options(
        "/health",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    return res.headers.get("access-control-allow-origin")


@pytest.fixture
def client(client_factory: Callable[..., TestClient]) -> TestClient:
    return client_factory(Settings(_env_file=None, pages_project_name=PROJECT))


@pytest.mark.parametrize(
    "origin",
    [
        "https://codemap.pages.dev",
        "https://3f2a1b9c.codemap.pages.dev",
        "https://d1-project-setup.codemap.pages.dev",
    ],
)
def test_our_pages_origins_allowed(client: TestClient, origin: str) -> None:
    assert _preflight(client, origin) == origin
    res = client.get("/health", headers={"Origin": origin})
    assert res.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("origin", LOCAL_DEV_ORIGINS)
def test_local_dev_origins_allowed(client: TestClient, origin: str) -> None:
    assert _preflight(client, origin) == origin


@pytest.mark.parametrize(
    "origin",
    [
        "https://other.pages.dev",
        "https://evil-codemap.pages.dev",
        "https://codemap-evil.pages.dev",
        "https://codemap.other.pages.dev",
        "https://a.b.codemap.pages.dev",
        "https://codemap.pages.dev.evil.com",
        "https://codemap.pages.dev:8443",
        "https://codemapXpagesXdev",
        "http://codemap.pages.dev",
        "https://evil.example.com",
        "http://localhost:3000",
    ],
)
def test_other_origins_rejected(client: TestClient, origin: str) -> None:
    assert _preflight(client, origin) is None
    res = client.get("/health", headers={"Origin": origin})
    assert "access-control-allow-origin" not in res.headers


def test_without_pages_project_only_local_allowed(
    client_factory: Callable[..., TestClient],
) -> None:
    client = client_factory()
    assert _preflight(client, "https://codemap.pages.dev") is None
    assert _preflight(client, LOCAL_DEV_ORIGINS[0]) == LOCAL_DEV_ORIGINS[0]


@pytest.mark.parametrize(
    "value",
    ["", "*", ".*", "codemap.pages.dev", "https://codemap.pages.dev", "Codemap", "-codemap"],
)
def test_pages_project_name_must_be_plain_name(value: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, pages_project_name=value)
