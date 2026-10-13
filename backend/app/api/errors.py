"""에러 응답 형식 { code, message, request_id, detail? }.

detail은 개발 환경에서만 포함한다.
"""

import json
import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.request_id import HEADER as REQUEST_ID_HEADER
from app.api.request_id import get_request_id
from app.domain.errors import AppError

logger = logging.getLogger("app.errors")


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str
    detail: str | None = None


_HTTP_ERRORS: dict[int, tuple[str, str]] = {
    404: ("REQUEST_NOT_FOUND", "요청한 주소를 찾을 수 없습니다. 주소를 확인해 주세요."),
    405: (
        "REQUEST_METHOD_NOT_ALLOWED",
        "지원하지 않는 요청 방식입니다. 요청 방식을 확인해 주세요.",
    ),
}
_HTTP_ERROR_FALLBACK = ("REQUEST_FAILED", "요청을 처리하지 못했습니다. 다시 시도해 주세요.")


def _respond(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    detail: str | None,
) -> JSONResponse:
    request_id = get_request_id(request)
    body: dict[str, str] = {"code": code, "message": message, "request_id": request_id}
    if request.app.state.settings.is_development and detail is not None:
        body["detail"] = detail
    # 예상 못한 예외는 미들웨어 바깥에서 응답하므로 헤더를 여기서도 붙인다.
    return JSONResponse(body, status_code=status_code, headers={REQUEST_ID_HEADER: request_id})


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    if exc.status_code >= 500:
        logger.warning("%s request_id=%s detail=%s", exc.code, get_request_id(request), exc.detail)
    return _respond(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        detail=exc.detail,
    )


async def _handle_http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code, message = _HTTP_ERRORS.get(exc.status_code, _HTTP_ERROR_FALLBACK)
    return _respond(
        request, status_code=exc.status_code, code=code, message=message, detail=str(exc.detail)
    )


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return _respond(
        request,
        status_code=422,
        code="REQUEST_INVALID",
        message="요청 형식이 올바르지 않습니다. 입력값을 확인해 주세요.",
        detail=json.dumps(jsonable_encoder(exc.errors()), ensure_ascii=False),
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("INTERNAL_ERROR request_id=%s", get_request_id(request))
    return _respond(
        request,
        status_code=500,
        code="INTERNAL_ERROR",
        message="서버에서 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        detail=repr(exc),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
