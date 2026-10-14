class AppError(Exception):
    """사용자에게 보여줄 에러. api 계층이 { code, message, request_id, detail? }로 바꿔 응답한다.

    code: "영역_무엇" 대문자 (예: ANALYSIS_REPO_TOO_LARGE)
    message: 무엇을 하면 되는지 포함한 한국어 문장
    detail: 개발 환경에서만 응답에 포함
    """

    def __init__(
        self, *, status_code: int, code: str, message: str, detail: str | None = None
    ) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail
