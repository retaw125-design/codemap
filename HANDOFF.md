# HANDOFF — D1 진행 상황 (2026-10-13)

브랜치: `d1-project-setup` (push 안 함). 계획 원본: `~/.claude/plans/pasted-content-id-1dd9-claude-md-docs-polished-eich.md`
D1 완료 기준: 배포 링크가 열리고, 백엔드 스키마를 바꾸면 프론트 타입이 자동 생성됨.

## 1. 완료한 것

### 백엔드 (끝남, 검사 전부 통과)
- `uv run pytest` 42개 통과, `ruff check`·`ruff format --check`·`mypy`(strict) 통과.
- 실제 서버(uvicorn)로 확인함:
  - DB 없음 → `/health` 503 `DATABASE_UNAVAILABLE`, 운영 모드에서 detail 없음
  - 닿지 않는 DB → 3초 뒤 503, 개발 모드에서 detail 포함
  - CORS: 미리보기 주소 허용, 다른 프로젝트 주소 거절
- 파일
  - `app/config.py`: 설정. 모든 값에 기본값이 있어 import만으로 환경변수를 요구하지 않음. CORS 허용 주소 계산.
  - `app/domain/errors.py`: `AppError` (순수 Python. 모든 계층이 던질 수 있음)
  - `app/api/errors.py`: `ErrorResponse` 스키마, 예외 처리기 (404·405·422·AppError·예상 못한 예외)
  - `app/api/request_id.py`: `X-Request-ID` 미들웨어 (안전한 형식만 재사용)
  - `app/api/health.py`: `GET /health`, DB 확인 함수는 의존성으로 주입
  - `app/infrastructure/persistence/db.py`: psycopg 풀 열기·ping
  - `app/main.py`: `create_app()`, DB 풀은 lifespan에서만 생성
  - `app/worker.py`: D2용 빈 진입점
  - `scripts/export_openapi.py`: 서버·DB 없이 OpenAPI를 `frontend/src/api/openapi.json`으로 내보냄
  - 배포: `Dockerfile`(uv 0.13.0, python:3.12-slim, 비 root 사용자), `.dockerignore`, `railway.json`(헬스체크 `/health`)
  - `.env.example`: `APP_ENV`, `DATABASE_URL`, `PAGES_PROJECT_NAME`
- 테스트: `tests/test_errors.py`, `test_health.py`, `test_cors.py`, `test_openapi_export.py`
  - `test_openapi_export.py`는 환경변수 없이, 그리고 닿지 않는 DB 주소로 하위 프로세스에서 내보내기를 실행해 본다.
  - 같은 파일에서 create_app만으로는 풀이 생기지 않고 lifespan에서만 생기는지도 확인한다.

### 프론트엔드 (진행 중)
- Vite(react-ts) 뼈대를 만들고 템플릿 부속물(oxlint, README, assets, public, App.css, index.css)을 삭제함.
- 패키지 설치 완료(`package-lock.json`). `openapi-fetch`, 그리고 개발용 패키지:
  - 타입·생성: TypeScript 5.9, openapi-typescript
  - 린트·포맷: eslint, typescript-eslint, react-hooks·react-refresh 플러그인, prettier, eslint-config-prettier
  - 테스트: vitest, jsdom, Testing Library
- `package.json` 스크립트 작성: dev, build, lint, format, format:check, typecheck, test, gen:api
- 두 tsconfig에 `"strict": true` 추가.
- `npm run gen:api` 동작 확인: `src/api/openapi.json`과 `src/api/generated/schema.d.ts` 생성됨 (`ErrorResponse` 포함).
- `vite.config.ts`에 vitest 설정(jsdom, setup 파일), `src/test/setup.ts` 작성.
- `src/App.test.tsx` 작성 (정상 / 에러 응답 / 연결 실패 3가지).

## 2. 남은 단계

### 다음 첫 작업: 프론트 테스트를 실행해 실패를 확인한 뒤 구현
1. `cd frontend && npm test` → 실패 확인 (`./api/client`가 아직 없음).
2. 아래 파일 작성:
   - `src/api/client.ts`: `createApiClient({ baseUrl, fetch? })`(openapi-fetch, `paths` 타입), 기본 클라이언트, `ErrorResponse = components['schemas']['ErrorResponse']` 별칭
   - `src/App.tsx`: 템플릿 코드를 교체. `client` prop(기본값 기본 클라이언트)으로 `/health`를 호출해 표시한다.
     - 정상: "API 정상 · DB 정상"
     - 에러 응답: 서버의 message와 `request_id`
     - 연결 실패: "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요."
   - `src/main.tsx`: 삭제한 `./index.css` import 제거
   - `src/vite-env.d.ts`: `VITE_API_BASE_URL` 타입 선언
   - `index.html`: `lang="ko"`, 제목 CodeMap, 없는 favicon 링크 제거
   - `.env.example`: `VITE_API_BASE_URL`
   - `eslint.config.js` (generated 폴더 제외, prettier와 충돌 끔), `.prettierrc`(세미콜론 없음, 작은따옴표 — 템플릿 스타일), `.prettierignore`(generated, openapi.json, dist, package-lock.json)
   - `src/{features,render,analysis,ui}/.gitkeep`
3. `npm test`, `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm run build` 통과시키기.

### 그다음
4. CI `.github/workflows/ci.yml` — 모든 브랜치 push·PR. 잡 5개:
   - backend: `uv sync --locked` → ruff check → ruff format --check → mypy → pytest
   - frontend: `npm ci` → lint → format:check → typecheck → test → build
   - api-types: `npm run gen:api` 후 `git diff --exit-code frontend/src/api`
   - secrets: gitleaks 바이너리로 전체 이력 검사
   - docker: `backend/Dockerfile`로 이미지 빌드(push 없음). 로컬에 Docker가 없어 배포 전에 CI에서 검증한다.
5. 배포 (사용자 계정 작업 필요, 아래 "사용자가 할 일")
6. 완료 기준 확인:
   - Pages 주소에서 "API 정상 · DB 정상"이 보이는지
   - `/health` 응답에 필드를 하나 추가하면 api-types 잡이 실패하는지, `npm run gen:api` 후 타입에 반영되는지
7. CLAUDE.md "명령어" 항목을 실제 명령어로 채우기, `docs/decision-log.md`에 아래 결정 기록, reviewer 에이전트 검토, PR 생성(main 병합은 사용자 승인 후)

### 사용자가 할 일 (배포 전)
- Supabase 프로젝트 2개(운영·시험), 각각 Session pooler 연결 문자열 준비. 로컬 `backend/.env`에는 시험용 주소를 넣는다.
- Railway
  - 저장소 연결, Root Directory `backend`
  - 설정 파일 경로 `/backend/railway.json` 지정 (Railway 설정 파일은 Root Directory를 따르지 않음)
  - 변수: `DATABASE_URL`, `APP_ENV=production`, `PAGES_PROJECT_NAME`
  - 공개 도메인 생성, "Wait for CI" 켜기
- Cloudflare Pages
  - Root `frontend`, 빌드 명령 `npm run build`, 출력 `dist`
  - 변수: `VITE_API_BASE_URL`(Railway 주소), `NODE_VERSION=24`
- GitHub main 브랜치 보호: PR 필수, CI 통과 필수

## 3. 중간에 내린 결정과 이유 (decision-log에 옮길 것)
| 결정 | 이유 |
|---|---|
| 정적 호스팅은 Cloudflare Pages | 사용자 선택. 무료, PR 미리보기 제공 |
| 타입 생성은 명령 1개(`npm run gen:api`) + CI 최신 여부 검사 | 사용자 선택. 단순하고 확실함 |
| openapi-typescript(타입만) + openapi-fetch | 변환 계층 없이 snake_case 그대로, 의존성 작음 |
| CORS는 `PAGES_PROJECT_NAME` + 정규식 `^https://(?:[a-z0-9-]+\.)?<이름>\.pages\.dev$` | 사용자 요청. PR 미리보기 주소는 허용하고 다른 프로젝트의 pages.dev는 거절. 이름에 점이 없도록 검증해 정규식이 넓어지지 않게 함. 로컬은 `localhost:5173`, `127.0.0.1:5173`만 허용. 사용자 지정 도메인이 생기면 설정 추가 필요 |
| DB 풀은 lifespan에서만 생성, 설정값은 전부 기본값 있음 | 사용자 요청. import·OpenAPI 내보내기·CI가 DB 없이 돌아가야 함 |
| DB 없이도 앱은 뜨고 `/health`가 503 | Railway 헬스체크가 실패해 잘못된 배포가 교체되지 않음 |
| `AppError`를 `domain/errors.py`에 둠 | 처음엔 api에 뒀으나 infrastructure → api 의존이 생겨 의존 방향 규칙 위반. 순수 Python이라 domain에 둬도 규칙에 맞음 |
| psycopg 3 + psycopg_pool | D1은 `/health`의 `select 1`만 사용. RLS용 사용자 토큰 접근 방식은 D2에서 결정 |
| Python 검사는 ruff + mypy(strict) | 린트·포맷 하나로, 타입 검사는 표준 도구 |
| 테스트 HTTP 클라이언트는 httpx → httpx2 | Starlette가 httpx 사용을 deprecated로 경고 |
| oxlint 대신 eslint | Vite 최신 템플릿 기본값이 oxlint였으나 CLAUDE.md와 승인된 계획이 eslint |
| TypeScript 6 대신 5.9 고정 | openapi-typescript 7.13(최신)의 peer가 `typescript ^5.x`이고 TS6 지원 버전이 없음. `--legacy-peer-deps`로 덮지 않고 지원 조합을 씀. 지원 버전이 나오면 올린다. TS 5.9는 strict가 기본이 아니라 명시함 |
| Tailwind·shadcn/ui는 D6으로 미룸 | D1 화면은 헬스 상태 한 줄. 디자인 규칙은 D6에 고정 |
| 공용 픽스처 양쪽 실행 CI 단계는 D11에 추가 | D1에는 픽스처가 없음 |
| Docker 이미지 로컬 빌드 미확인 | 이 맥에 docker가 없음. CI/Railway가 첫 빌드 |

## 4. 알려진 이슈
- ~~**npm 캐시 권한**~~ (2026-10-13 사용자가 chown으로 해결, 기본 캐시 정상 동작 확인): `~/.npm` 안의 파일 590개가 root 소유라서(이전에 `sudo npm`을 쓴 흔적) npm이 `EACCES`로 실패한다.
  - 이번 세션은 임시 캐시(`npm_config_cache=<세션 스크래치패드>/npm-cache`)로 우회했다.
  - 사용자가 직접 실행해서 고칠 것: `sudo chown -R $(id -u):$(id -g) ~/.npm`
- **프론트 빌드는 지금 깨져 있음**: `src/App.tsx`는 아직 템플릿 코드여서 삭제한 assets와 `App.css`를 import한다. `src/main.tsx`도 삭제한 `index.css`를 import한다. 다음 첫 작업에서 고친다.
- `frontend/.gitignore`는 Vite 템플릿 것이 그대로 있다. 루트 `.gitignore`와 내용이 겹치지만 문제는 없다.
- Railway 설정 파일 경로는 대시보드에서 `/backend/railway.json`으로 직접 지정해야 한다.

## 5. 지금 상태 (2026-10-13 갱신)
- 백엔드: 완료, 검사 전부 통과.
- 프론트: 완료. `client.ts`, `App.tsx` 등 "다음 첫 작업" 2번 목록 전부 작성. test(3개)·lint·format:check·typecheck·build 통과.
- CI: `.github/workflows/ci.yml` 잡 5개(backend, frontend, api-types, secrets, docker) 전부 GitHub에서 통과(실행 38374283985).
  - docker 잡은 이미지 빌드 후 컨테이너를 DB 없이 띄워 `/health`가 503 `DATABASE_UNAVAILABLE`을 주는 것까지 확인한다.
  - `astral-sh/setup-uv`는 주 버전 태그(v10)가 없어 정확한 버전(v10.3.0)으로 고정해야 한다.
  - 10월 19일부터 `ubuntu-latest`가 Ubuntu 26으로 바뀐다. 그 뒤 CI가 깨지면 먼저 확인할 것.
- CLAUDE.md "명령어" 채움, "작업 방식"에 한국어 규칙 추가. decision-log에 3절 결정 기록 완료.
- 브랜치 push 완료(origin/d1-project-setup).
- Railway 배포 완료: https://codemap-production-7c81.up.railway.app (싱가포르, `d1-project-setup` 브랜치, Root `/backend`, CI 대기 켬, 포트 8080)
  - `/health` → 200 `{"status":"ok","database":"ok"}`, 없는 주소 → 404 `REQUEST_NOT_FOUND` 형식 확인.
  - Supabase 운영 프로젝트도 싱가포르(ap-southeast-1), Session pooler + `?sslmode=require`.
  - 운영 DB 비밀번호는 대화에 노출되어 2026-10-13 교체함(교체 후 재배포 ACTIVE, `/health` 정상).
  - `PAGES_PROJECT_NAME`은 아직 안 넣음: Pages 실제 주소 확인 후 넣는다.
  - main 병합 후 Railway 브랜치를 `main`으로 되돌려야 한다.
- 남은 것: 배포(사용자 계정 작업) → 완료 기준 확인 → reviewer 에이전트 검토 → PR.
