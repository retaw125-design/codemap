# HANDOFF — D1 상태 (2026-10-14)

브랜치: `d1-project-setup` (origin에 push됨). 남은 것: PR → 사용자 승인 후 main 병합 → 아래 "병합 후 할 일".
D1 완료 기준: 배포 링크가 열리고, 백엔드 스키마를 바꾸면 프론트 타입이 자동 생성됨. **두 기준 모두 확인함(아래 3절).**
결정과 이유는 `docs/decision-log.md`(2026-10-13·14 항목)에 옮겨 두었다.

## 1. 만든 것
### 백엔드 (`backend/`)
- `app/config.py`: 설정. 모든 값에 기본값이 있어 import만으로 환경변수를 요구하지 않음. `APP_ENV` 기본값은 `production`(빠뜨려도 detail이 새지 않음). CORS 허용 주소 계산.
- `app/domain/errors.py`: `AppError` (순수 Python)
- `app/api/errors.py`: `ErrorResponse`, 예외 처리기(404·405·422·AppError·예상 못한 예외), `UnexpectedErrorMiddleware`(500 응답에도 CORS 헤더가 붙도록 CORS 안쪽에서 처리)
- `app/api/request_id.py`: `X-Request-ID` 미들웨어 (안전한 형식만 재사용)
- `app/api/health.py`: `GET /health`, DB 확인 함수는 의존성으로 주입
- `app/infrastructure/persistence/db.py`: psycopg 풀 열기·ping
- `app/main.py`: `create_app()`, DB 풀은 lifespan에서만 생성
- `app/worker.py`: D2용 빈 진입점
- `scripts/export_openapi.py`: 서버·DB 없이 OpenAPI를 `frontend/src/api/openapi.json`으로 내보냄
- 배포: `Dockerfile`(uv 0.13.0, python:3.12-slim, 비 root), `.dockerignore`, `railway.json`(헬스체크 `/health`)
- 테스트 44개: `test_errors.py`, `test_health.py`, `test_cors.py`, `test_openapi_export.py`

### 프론트엔드 (`frontend/`)
- Vite + React + TypeScript 5.9(strict), eslint + prettier, vitest + Testing Library
- `src/api/client.ts`: openapi-fetch 클라이언트(`createApiClient`, 기본 `apiClient`), `ErrorResponse` 별칭
- `src/App.tsx`: `/health` 상태 표시(정상 / 서버 에러 message·request_id / 연결 실패), 테스트 3개
- `vite.config.ts`: Cloudflare Pages 빌드(`CF_PAGES`)에서 `VITE_API_BASE_URL`이 없으면 빌드 실패
- `npm run gen:api`: OpenAPI → `src/api/generated/schema.d.ts`

### CI (`.github/workflows/ci.yml`, 모든 브랜치 push·PR)
- backend: ruff check, ruff format --check, mypy(strict), pytest
- frontend: lint, format:check, typecheck, test, build
- api-types: `gen:api` 후 `frontend/src/api`에 변경이나 새 파일이 있으면 실패
- secrets: gitleaks 8.30.1(체크섬 확인)로 전체 이력 검사
- docker: 이미지 빌드 → DB 없이 컨테이너 기동 → `/health` 503 `DATABASE_UNAVAILABLE`이고 `detail`이 없는지 확인
- 참고: `astral-sh/setup-uv`는 주 버전 태그(v10)가 없어 정확한 버전으로 고정해야 한다. 10월 19일부터 `ubuntu-latest`가 Ubuntu 26으로 바뀐다. 그 뒤 CI가 깨지면 먼저 확인.

## 2. 배포 상태
- **Railway (백엔드)**: https://codemap-production-7c81.up.railway.app
  - 싱가포르, 브랜치 `d1-project-setup`, Root `/backend`, 설정 파일 `/backend/railway.json`(Root를 따르지 않아 직접 지정), Wait for CI 켬, 포트 8080
  - 변수: `DATABASE_URL`, `APP_ENV=production`, `PAGES_PROJECT_NAME=codemap-bq7`
  - Wait for CI가 Railway 자신의 검사 항목 대기로 1분쯤 멈출 때가 있다. 계속 멈추면 Redeploy.
- **Supabase (운영 DB)**: 싱가포르(ap-southeast-1), Session pooler + `?sslmode=require`
  - 운영 DB 비밀번호는 대화에 노출되어 2026-10-13 교체함.
  - 시험용 프로젝트는 로컬 `backend/.env`에 넣는다.
- **Cloudflare Pages (프론트)**: https://codemap-bq7.pages.dev
  - 프로젝트 이름은 `codemap`이지만 배정된 주소는 `codemap-bq7`. 그래서 `PAGES_PROJECT_NAME`에는 주소 앞부분을 쓴다.
  - 브랜치 `d1-project-setup`, Root `frontend`, 빌드 `npm run build`, 출력 `dist`
  - 변수(Text): `VITE_API_BASE_URL`, `NODE_VERSION=24`. 변수 이름 칸에 다른 글자가 섞여 localhost로 빌드된 적이 있어 빌드 검사를 추가함.

## 3. D1 완료 기준 확인 (2026-10-14)
1. Pages 주소를 브라우저로 열어 "API 정상 · DB 정상" 표시 확인.
2. `HealthResponse`에 필드를 임시로 추가 → `gen:api` 결과가 커밋된 파일과 달라짐(CI api-types 실패 조건) → `npm run gen:api` 후 `schema.d.ts`에 반영됨. 확인 후 원상 복구.

## 4. 병합 후 할 일
- Railway와 Cloudflare Pages의 운영 브랜치를 `main`으로 되돌린다.
- GitHub main 브랜치 보호: PR 필수, CI 통과 필수.

## 5. 알려진 이슈
- `frontend/.gitignore`는 Vite 템플릿 것이 그대로 있다. 루트 `.gitignore`와 겹치지만 문제없음.
- 로컬에 Docker가 없다. 이미지 검증은 CI docker 잡이 한다.
