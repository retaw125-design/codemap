"""CORS는 Cloudflare Pages 주소와 로컬 개발 주소만 허용한다."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import LOCAL_DEV_ORIGINS, Settings

PAGES_ORIGIN = "https://codemap.pages.dev"


def _preflight(client: TestClient, origin: str) -> str | None:
    res = client.options(
        "/health",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    return res.headers.get("access-control-allow-origin")


@pytest.fixture
def client(client_factory: Callable[..., TestClient]) -> TestClient:
    return client_factory(Settings(_env_file=None, frontend_origin=PAGES_ORIGIN))


def test_pages_origin_allowed(client: TestClient) -> None:
    assert _preflight(client, PAGES_ORIGIN) == PAGES_ORIGIN
    res = client.get("/health", headers={"Origin": PAGES_ORIGIN})
    assert res.headers["access-control-allow-origin"] == PAGES_ORIGIN


@pytest.mark.parametrize("origin", LOCAL_DEV_ORIGINS)
def test_local_dev_origins_allowed(client: TestClient, origin: str) -> None:
    assert _preflight(client, origin) == origin


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example.com",
        "https://preview.codemap.pages.dev",
        "https://codemap.pages.dev.evil.com",
        "http://codemap.pages.dev",
        "http://localhost:3000",
    ],
)
def test_other_origins_rejected(client: TestClient, origin: str) -> None:
    assert _preflight(client, origin) is None
    res = client.get("/health", headers={"Origin": origin})
    assert "access-control-allow-origin" not in res.headers


def test_without_frontend_origin_only_local_allowed(
    client_factory: Callable[..., TestClient],
) -> None:
    client = client_factory()
    assert _preflight(client, PAGES_ORIGIN) is None
    assert _preflight(client, LOCAL_DEV_ORIGINS[0]) == LOCAL_DEV_ORIGINS[0]


@pytest.mark.parametrize(
    "value",
    ["*", "http://codemap.pages.dev", "https://codemap.pages.dev/", "https://example.com"],
)
def test_frontend_origin_must_be_pages_https_origin(value: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, frontend_origin=value)
