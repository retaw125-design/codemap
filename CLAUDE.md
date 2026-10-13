# CodeMap (가칭) — 프로젝트 규칙

## 이 프로젝트는
코드를 읽을 줄은 알지만 구조가 안 보이는 개발 학습자가, 공개 GitHub 저장소를 2.5D 층 지도로 보며
"어디를 바꾸면 어디에 영향이 가는지" 훈련하는 서비스다. 상세는 `docs/01-product.md`.

## 작업 시작 전
1. 오늘 작업과 완료 기준을 `docs/06-dev-and-deploy.md`에서 확인한다.
2. 관련 문서(`docs/03-architecture.md`, `docs/04-data-model.md`)를 읽는다.
3. 완료 기준이 모호하거나 설계 결정이 필요하면, 구현 전에 사람에게 묻는다.

## 절대 규칙 (보안)
- 가져온 저장소의 코드는 절대 실행, import, eval 하지 않는다. 읽기(파싱)만 한다.
- 저장소는 내려받기 전에 GitHub API로 크기를 확인하고, 상한을 넘으면 거절한다.
- git clone 대신 압축 파일(tarball)로 받는다. 압축 해제 총량에도 상한을 둔다.
- 심볼릭 링크는 따라가지 않고 건너뛴다.
- API 키와 토큰은 환경변수로만 다룬다. 코드, 로그, 테스트 픽스처에 넣지 않는다.
- `human_grades`(사람이 채점한 평가셋)는 AI가 생성하거나 수정하지 않는다.

## 아키텍처 규칙
- 의존 방향: `api → application → domain ← infrastructure`
- `domain`은 순수 Python이다. DB, HTTP, OpenAI, 파일시스템을 import하지 않는다.
- 인터페이스(Protocol)는 저장소와 LLM 게이트웨이에만 만든다. 그 외에는 추상화하지 말고 함수로 작성한다.
- 코드 추출 규칙은 `shared/queries/`의 tree-sitter 쿼리로만 작성한다. 서버나 브라우저 코드에 추출 로직을 하드코딩하지 않는다.
- 무거운 파싱은 별도 프로세스 풀에서 실행한다. API 이벤트 루프에서 CPU 작업을 하지 않는다.

## API 계약
- JSON 필드는 서버와 클라이언트 모두 snake_case로 통일한다. 변환 계층을 두지 않는다.
- 프론트엔드 타입은 FastAPI의 OpenAPI 명세에서 자동 생성한다(`frontend/src/api/generated`). 손으로 작성하거나 수정하지 않는다.
- 에러 응답 형식: `{ code, message, request_id, detail? }`
  - `code`: "영역_무엇" 대문자 (예: `ANALYSIS_REPO_TOO_LARGE`, `LLM_UNAVAILABLE`)
  - `message`: 사용자에게 보여줄 한국어 문장 (무엇을 하면 되는지 포함)
  - `detail`: 개발 환경에서만 포함

## 그래프 규칙
- 노드 ID: `{상대경로}::{전체이름}` (예: `app/services/feed.py::FeedService.recommend`). 모듈 노드는 경로만 쓴다.
- 노드 필드: `id, kind, layer, role, file, span, body_hash, metrics`
- 연결 필드: `from, to, kind(import|call|inherit), confidence(exact|inferred)`
- 그래프 형식을 바꾸면 `schema_version`을 올린다. 구버전 그래프는 변환하지 않고 재분석한다.

## LLM 규칙
- OpenAI 호출은 `infrastructure/llm/gateway`를 통해서만 한다.
- 구조화된 출력(JSON 스키마)을 반드시 사용한다.
- 프롬프트는 고정 부분(지시문, 저장소 요약)을 앞에, 바뀌는 부분(문제, 답안)을 뒤에 둔다. 프롬프트 캐시 적중을 위해서다.
- 모든 호출을 `llm_calls`에 기록한다(모델, 토큰, 캐시 토큰, 비용, 지연, 결과).
- 연속 실패 시 차단기가 열리고, 규칙 기반 기능만 동작한다.
- LLM이 만든 정답의 노드는 그래프에 실제로 존재하는지 규칙으로 검증한 뒤에만 저장한다.

## 테스트 규칙
- 순서: 완료 기준 → 실패하는 테스트 작성 → 구현.
- `domain`의 함수는 단위 테스트가 필수다.
- `shared/fixtures`의 케이스는 서버(pytest)와 브라우저(vitest) 양쪽에서 실행하고, 결과가 같아야 한다.
- 테스트에서 OpenAI를 실제로 호출하지 않는다. 가짜 응답을 쓴다.

## 작업 방식
- 작업마다 브랜치를 만든다. CI 통과와 사람 승인 후에만 main에 합친다.
- 한 번에 하나의 D-작업만 한다. 범위 밖 개선은 하지 말고 `docs/decision-log.md`에 후보로 남긴다.
- 작업이 끝나면 바꾼 파일, 내린 판단, 남은 문제를 짧게 보고한다.
- 모든 답변, 작업 설명, 명령 승인 요청의 설명 문구는 한국어로 작성한다.

## 명령어 (D1에 확정 후 채운다)
- 백엔드 테스트: (예정) pytest
- 프론트엔드 테스트: (예정) vitest
- 린트·포맷: (예정) ruff, eslint, prettier
- API 타입 생성: (예정) OpenAPI → TypeScript 생성 도구

## 폴더 구조
```
codemap/
├── CLAUDE.md
├── docs/
├── shared/
│   ├── queries/python/       # 추출 규칙 (서버·브라우저 공용)
│   └── fixtures/             # 공용 테스트 케이스
├── backend/
│   ├── app/
│   │   ├── api/              # 라우터, 요청·응답 스키마
│   │   ├── application/
│   │   │   ├── analysis/
│   │   │   └── learning/
│   │   ├── domain/
│   │   │   ├── analysis/     # 그래프, 영향 범위, 레이어 판정, 저장소 인터페이스
│   │   │   └── learning/     # 문제, 풀이 기록, 채점 규칙, 저장소 인터페이스
│   │   ├── infrastructure/
│   │   │   ├── parsing/      # 언어 어댑터, 프레임워크 인식기
│   │   │   ├── persistence/  # Supabase 저장소, 작업 큐
│   │   │   ├── llm/          # 게이트웨이, OpenAI 클라이언트, 캐시, 차단기
│   │   │   └── git/          # 저장소 가져오기
│   │   └── worker.py
│   └── tests/
└── frontend/
    └── src/
        ├── api/              # 자동 생성 타입 + 클라이언트
        ├── features/         # map, editor, compare, practice
        ├── render/           # 입체 투영, 모양, 빛 효과
        ├── analysis/         # 실시간 재분석, 영향 범위 계산
        └── ui/               # 패널, 테마
```
