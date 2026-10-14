from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.errors import ErrorResponse

# DB에 연결할 수 없으면 AppError(DATABASE_UNAVAILABLE)를 던진다. main.py의 lifespan이 주입한다.
DatabaseCheck = Callable[[], Awaitable[None]]

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]


def get_database_check(request: Request) -> DatabaseCheck:
    check: DatabaseCheck = request.app.state.check_database
    return check


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": ErrorResponse, "description": "DB에 연결할 수 없음"}},
)
async def health(
    check_database: Annotated[DatabaseCheck, Depends(get_database_check)],
) -> HealthResponse:
    await check_database()
    return HealthResponse(status="ok", database="ok")
