"""에러 응답 형식 { code, message, request_id, detail? }과 request_id 전파."""

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.config import Settings
from app.domain.errors import AppError


def _assert_error_shape(body: dict[str, object], code: str) -> None:
    assert body["code"] == code
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["request_id"], str) and body["request_id"]
    assert set(body) <= {"code", "message", "request_id", "detail"}


def _add_test_routes(app: FastAPI) -> None:
    class Item(BaseModel):
        name: str

    @app.get("/_test/app-error")
    async def raise_app_error() -> None:
        raise AppError(
            status_code=413,
            code="ANALYSIS_REPO_TOO_LARGE",
            message="저장소가 너무 큽니다. 더 작은 저장소로 다시 시도해 주세요.",
            detail="size=999MB",
        )

    @app.get("/_test/crash")
    async def crash() -> None:
        raise RuntimeError("boom")

    @app.post("/_test/items")
    async def create_item(item: Item) -> Item:
        return item


def _client(client_factory: Callable[..., TestClient], app_env: str) -> TestClient:
    client = client_factory(Settings(_env_file=None, app_env=app_env))
    _add_test_routes(client.app)  # type: ignore[arg-type]
    return client


def test_not_found_uses_error_format(client: TestClient) -> None:
    res = client.get("/does-not-exist")
    assert res.status_code == 404
    _assert_error_shape(res.json(), "REQUEST_NOT_FOUND")


def test_validation_error_uses_error_format(client_factory: Callable[..., TestClient]) -> None:
    res = _client(client_factory, "development").post("/_test/items", json={"wrong": 1})
    assert res.status_code == 422
    _assert_error_shape(res.json(), "REQUEST_INVALID")


def test_app_error_keeps_code_and_status(client_factory: Callable[..., TestClient]) -> None:
    res = _client(client_factory, "development").get("/_test/app-error")
    assert res.status_code == 413
    body = res.json()
    _assert_error_shape(body, "ANALYSIS_REPO_TOO_LARGE")
    assert body["message"] == "저장소가 너무 큽니다. 더 작은 저장소로 다시 시도해 주세요."


def test_unexpected_exception_becomes_internal_error(
    client_factory: Callable[..., TestClient],
) -> None:
    res = _client(client_factory, "development").get("/_test/crash")
    assert res.status_code == 500
    _assert_error_shape(res.json(), "INTERNAL_ERROR")


def test_detail_included_only_in_development(client_factory: Callable[..., TestClient]) -> None:
    dev = _client(client_factory, "development")
    prod = _client(client_factory, "production")

    assert dev.get("/_test/app-error").json()["detail"] == "size=999MB"
    assert "boom" in dev.get("/_test/crash").json()["detail"]

    for path in ("/_test/app-error", "/_test/crash", "/does-not-exist"):
        assert "detail" not in prod.get(path).json(), path
    assert "detail" not in prod.post("/_test/items", json={}).json()


def test_request_id_header_matches_error_body(client_factory: Callable[..., TestClient]) -> None:
    client = _client(client_factory, "production")
    for res in (client.get("/does-not-exist"), client.get("/_test/crash")):
        assert res.headers["x-request-id"] == res.json()["request_id"]


def test_request_id_is_generated_and_attached_to_success(client: TestClient) -> None:
    first = client.get("/health").headers["x-request-id"]
    second = client.get("/health").headers["x-request-id"]
    assert first and second and first != second


def test_incoming_request_id_is_reused(client: TestClient) -> None:
    res = client.get("/does-not-exist", headers={"X-Request-ID": "trace-abc-123"})
    assert res.headers["x-request-id"] == "trace-abc-123"
    assert res.json()["request_id"] == "trace-abc-123"


def test_unsafe_incoming_request_id_is_replaced(client: TestClient) -> None:
    unsafe = "bad id\nwith newline" + "x" * 100
    res = client.get("/health", headers={"X-Request-ID": unsafe.replace("\n", " ")})
    assert res.headers["x-request-id"] != unsafe.replace("\n", " ")
