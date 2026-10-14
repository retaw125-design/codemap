import re
import uuid

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

HEADER = "X-Request-ID"
_SAFE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def get_request_id(request: Request) -> str:
    request_id: str | None = getattr(request.state, "request_id", None)
    return request_id or new_request_id()


def new_request_id() -> str:
    return uuid.uuid4().hex


class RequestIdMiddleware:
    """요청마다 request_id를 정하고 응답 헤더에 붙인다.

    들어온 X-Request-ID가 안전한 형식이면 그대로 쓴다 (로그 주입 방지).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Request(scope).headers.get(HEADER, "")
        request_id = incoming if _SAFE.fullmatch(incoming) else new_request_id()
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                if HEADER not in headers:
                    headers[HEADER] = request_id
            await send(message)

        await self.app(scope, receive, send_with_id)
