"""OpenAPI 명세를 파일로 내보낸다. 서버나 DB 없이 동작한다.

사용: uv run python -m scripts.export_openapi [출력 경로]
기본 출력: ../frontend/src/api/openapi.json (npm run gen:api가 이 파일로 타입을 만든다)
"""

import json
import sys
from pathlib import Path

from app.config import Settings
from app.main import create_app

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "api" / "openapi.json"


def export(out: Path) -> None:
    # .env를 읽지 않는다: 명세는 개발자 컴퓨터의 설정과 무관하게 같아야 한다.
    spec = create_app(Settings(_env_file=None)).openapi()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    export(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT)
