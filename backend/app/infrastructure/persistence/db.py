from psycopg_pool import AsyncConnectionPool

from app.domain.errors import AppError

PING_TIMEOUT_SECONDS = 3.0


def database_unavailable(detail: str) -> AppError:
    return AppError(
        status_code=503,
        code="DATABASE_UNAVAILABLE",
        message="데이터베이스에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.",
        detail=detail,
    )


async def open_pool(database_url: str) -> AsyncConnectionPool:
    """앱 시작 시점(lifespan)에만 호출한다.

    연결은 백그라운드에서 맺으므로 DB가 없어도 앱 시작은 된다.
    """
    pool = AsyncConnectionPool(database_url, min_size=1, max_size=5, open=False)
    await pool.open(wait=False)
    return pool


async def ping(pool: AsyncConnectionPool) -> None:
    try:
        async with pool.connection(timeout=PING_TIMEOUT_SECONDS) as conn:
            await conn.execute("select 1")
    except Exception as exc:
        raise database_unavailable(f"{type(exc).__name__}: {exc}") from exc


async def no_database() -> None:
    raise database_unavailable("DATABASE_URL is not set")
