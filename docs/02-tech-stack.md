# 02. 기술 스택 (PHASE 2)

원칙: 트렌디한 것보다 이 프로젝트에 맞는 것. 과도한 설계보다 적절한 복잡도.

## 결정 기록
| 결정 | 선택 | 대안 | 이유 |
|---|---|---|---|
| 코드 분석 | Python + tree-sitter | Python 내장 ast | 언어 선택 기능을 위해 모든 언어를 같은 방식으로 파싱. 언어별 차이는 어댑터로 분리 |
| 백엔드 | FastAPI | NestJS | 이미 써봤고, 분석 엔진과 같은 언어 |
| 프론트 | Vite + React + TypeScript | Next.js | 검색 노출이 필요 없는 도구형 앱이라 서버 렌더링이 필요 없음 |
| 2.5D 렌더링 | SVG + ELK.js | Canvas/WebGL | 글자가 선명하고 클릭 처리가 쉬움. 느려지면 측정 후 전환 |
| DB | PostgreSQL (Supabase) | 그래프 DB | 저장소 하나의 그래프는 작아서 메모리 계산으로 충분 |
| 작업 큐 | Postgres 테이블 | Redis + RQ | 월 $5 제약 안에서 서비스 수를 줄임. SKIP LOCKED와 임대 만료로 구현 |
| 캐시 | Postgres 테이블 | Redis | 위와 같은 이유 |
| 벡터 검색 | 1차에서 제외 | pgvector | 문제 생성에 필요한 코드는 그래프에서 고르면 충분 |
| LLM | OpenAI API | - | 이미 결제한 계정 사용 |
| 인증 | Supabase Auth (GitHub 로그인) | 로그인 없음 | 사용자가 개발자라 자연스럽고, 풀이 기록에 계정 필요 |
| UI | Tailwind + shadcn/ui, Monaco | 직접 제작 | 디자인 시간 절약, 전문 도구 느낌 |
| 실시간 재분석 | web-tree-sitter | 서버 재요청 | 서버 부하 없이 즉시 반영 |

## 확정 스택
```
Frontend   : Vite + React + TypeScript, Tailwind + shadcn/ui, Monaco,
             SVG 2.5D + ELK.js, web-tree-sitter
Backend    : FastAPI + py-tree-sitter (언어 어댑터, 프레임워크 인식기)
Queue/Cache: Postgres 테이블 (Redis 없음)
DB / Auth  : Supabase (PostgreSQL, GitHub 로그인)
LLM        : OpenAI API (기본 mini, 단순 작업 nano, 구조화된 출력, 프롬프트 캐시)
Infra      : Railway Hobby (API 서버 1개) + Supabase + 정적 호스팅
CI/CD      : GitHub Actions
Monitoring : Sentry + llm_calls 테이블
나중에     : Pyodide (3차 동작 비교), Three.js (3차 3D 탐색)
```

## LLM 모델 배치
| 작업 | 모델 |
|---|---|
| 기능 추가 위치 문제 생성 | mini |
| 답안 이유 채점 | mini로 시작, nano와 비교 실험 |
| 단순 분류 | nano |
모델 라인업과 단가는 자주 바뀌므로 시작 시점에 OpenAI 가격 페이지에서 다시 확인한다.

## 월 비용 (예상)
| 항목 | 비용 |
|---|---|
| Railway Hobby | 약 $5 |
| OpenAI API | 몇 달러 (충전 크레딧에서 차감) |
| Supabase, 정적 호스팅, Sentry, CI | $0 (무료 등급) |
개발 초반에는 Render 무료 등급도 가능하지만, 15분 미사용 시 잠드는 문제가 있어 배포·데모 기간에는 Railway를 쓴다.

## 인증 보안
- 프론트엔드는 로그인에만 Supabase를 직접 쓰고, 모든 데이터는 FastAPI를 거친다.
- FastAPI는 사용자의 로그인 토큰으로 DB에 접근해 행 단위 접근 제한이 실제로 작동하게 한다.
- 무료 등급 LLM이 아니라 유료 API이므로 입력이 학습에 쓰이지 않는 정책이지만, 이용 안내에 "답안이 외부 AI로 전송된다"는 고지를 넣는다.
