# 설계 결정 기록

형식: 날짜 / 결정 / 대안 / 이유 / 결과(나중에 채움)

| 날짜 | 결정 | 대안 | 이유 | 결과 |
|---|---|---|---|---|
| 2026-10-10 | 아이디어: 코딩 구조 학습 AI | 재입고 추적, 현상수배 숨바꼭질 등 | 실사용자(동기) 확보 용이, AI 평가 수치 확보 가능, 빠른 완성 가능 | |
| 2026-10-10 | 2.5D 렌더링 | 진짜 3D | 글자 가독성, 정확한 클릭, 개발 기간 | |
| 2026-10-10 | 문제 유형을 영향 범위 → 기능 추가 위치 순으로 도입 | 처음부터 LLM 문제 | 규칙 정답으로 채점 시스템을 먼저 검증 | |
| 2026-10-10 | Vite + React | Next.js | 서버 렌더링 불필요 | |
| 2026-10-10 | Postgres로 작업 큐·캐시 | Redis + RQ | 월 $5 제약, 서비스 수 축소 | |
| 2026-10-10 | 추출 규칙을 tree-sitter 쿼리로 공유 | 서버·브라우저 각자 구현 | 분석 결과 불일치 방지 | |
| 2026-10-10 | 코드 그래프 JSONB 통째 저장 | 노드·연결 테이블 | 불변, 통째로 읽음, 행 단위 조회 불필요 | |
| 2026-10-10 | 코드 원문 미저장, 커밋 SHA 고정 | 원문 저장 | DB 500MB 제한 | |
| 2026-10-10 | 1차에서 pgvector 제외 | pgvector | 그래프로 충분, 쓰지 않을 기술 | |
| 2026-10-10 | API JSON snake_case 통일, 타입 자동 생성 | camelCase 변환 계층 | 필드 이름 불일치 버그 유형 제거 | |
| 2026-10-10 | OpenAI 기본 mini, 단순 작업 nano | - | 기존 결제 계정, 비교 실험으로 최종 결정 | |
| 2026-10-13 | 정적 호스팅은 Cloudflare Pages | Vercel, Netlify | 무료, PR 미리보기 제공 | |
| 2026-10-13 | 타입 생성은 `npm run gen:api` 1개 + CI 최신 여부 검사 | 파일 감시 자동 생성 | 단순하고 확실함 | |
| 2026-10-13 | openapi-typescript(타입만) + openapi-fetch | orval 등 코드 생성기 | 변환 계층 없이 snake_case 그대로, 의존성 작음 | |
| 2026-10-13 | CORS는 `PAGES_PROJECT_NAME` 기반 정규식 + 로컬 5173만 허용 | 모든 pages.dev 허용 | PR 미리보기는 허용하고 다른 프로젝트는 거절. 이름에 점 금지로 정규식이 넓어지지 않게 함. 사용자 지정 도메인이 생기면 설정 추가 필요 | |
| 2026-10-13 | DB 풀은 lifespan에서만 생성, 설정값은 전부 기본값 있음 | import 시 연결 | import·OpenAPI 내보내기·CI가 DB 없이 돌아가야 함 | |
| 2026-10-13 | DB 없이도 앱은 뜨고 `/health`가 503 | 시작 시 실패 | Railway 헬스체크가 실패해 잘못된 배포로 교체되지 않음 | |
| 2026-10-13 | `AppError`를 `domain/errors.py`에 둠 | api 계층 | api에 두면 infrastructure → api 의존이 생겨 의존 방향 규칙 위반 | |
| 2026-10-13 | psycopg 3 + psycopg_pool | asyncpg, supabase-py | D1은 `select 1`만 사용. RLS용 사용자 토큰 접근 방식은 D2에서 결정 | |
| 2026-10-13 | Python 검사는 ruff + mypy(strict) | flake8·black·pyright | 린트·포맷 하나로, 타입 검사는 표준 도구 | |
| 2026-10-13 | 테스트 HTTP 클라이언트 httpx → httpx2 | httpx 유지 | Starlette가 httpx 사용을 deprecated로 경고 | |
| 2026-10-13 | oxlint 대신 eslint | Vite 템플릿 기본 oxlint | CLAUDE.md와 승인된 계획이 eslint | |
| 2026-10-13 | TypeScript 5.9 고정 | TypeScript 6 + `--legacy-peer-deps` | openapi-typescript 7.13의 peer가 `typescript ^5.x`. 지원 버전이 나오면 올림 | |
| 2026-10-13 | Tailwind·shadcn/ui는 D6으로 미룸 | D1에 도입 | D1 화면은 헬스 상태 한 줄. 디자인 규칙은 D6에 고정 | |
| 2026-10-13 | 공용 픽스처 양쪽 실행 CI 단계는 D11에 추가 | D1에 빈 단계 | D1에는 픽스처가 없음 | |
| 2026-10-13 | 백엔드 Docker 이미지 빌드와 컨테이너 기동(DB 없이 `/health` 503) 검사를 CI에 추가 | Railway 첫 빌드에 맡김 | 로컬에 Docker가 없어 배포 전에 CI에서 검증해야 함 | |

## 범위 밖 개선 후보
(에이전트와 작업 중 떠오른 개선 아이디어를 여기에 적고, 범위 회의 때 판단한다)
