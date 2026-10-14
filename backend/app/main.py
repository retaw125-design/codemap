"""앱 조립. import와 create_app()은 DB 접속이나 환경변수를 요구하지 않는다.

DB 풀은 앱이 실제로 시작될 때(lifespan)만 만든다.
그래서 OpenAPI 내보내기와 테스트는 DB 없이 돌아간다.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api.errors import ErrorResponse, UnexpectedErrorMiddleware, register_error_handlers
from app.api.request_id import HEADER as REQUEST_ID_HEADER
from app.api.request_id import RequestIdMiddleware
from app.config import Settings
from app.infrastructure.persistence import db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    if settings.database_url is None:
        app.state.check_database = db.no_database
        yield
        return

    pool = await db.open_pool(settings.database_url)
    app.state.check_database = partial(db.ping, pool)
    try:
        yield
    finally:
        await pool.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="CodeMap API",
        version="0.1.0",
        lifespan=lifespan,
        # 모든 경로의 에러 응답을 ErrorResponse로 문서화한다 (기본 HTTPValidationError 대신).
        responses={"default": {"model": ErrorResponse, "description": "에러 응답"}},
    )
    app.state.settings = settings

    register_error_handlers(app)
    # CORS 안쪽에서 예상 못한 예외를 처리해 500 응답에도 CORS 헤더가 붙게 한다.
    app.add_middleware(UnexpectedErrorMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    # 마지막에 추가한 미들웨어가 가장 바깥에서 실행된다. CORS 응답에도 request_id가 붙는다.
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health.router)
    return app


app = create_app()
