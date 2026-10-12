# 04. 데이터 모델 (PHASE 4)

## 원칙
- 코드 그래프만 비정규화(JSONB 통째 저장), 나머지는 정규화. 그래프는 바뀌지 않고, 항상 통째로 읽고, SQL로 노드를 하나씩 조회할 일이 없다.
- 인덱스는 조회 패턴에 맞춰서만 건다.
- 전부 하드 삭제. 30일 동안 열리지 않은 그래프는 주기적으로 삭제한다.
- 모든 테이블에 `created_at`, 바뀔 수 있는 테이블에 `updated_at`.
- 코드 원문은 저장하지 않는다. 분석 시 커밋 SHA를 기록하고, 코드 뷰어는 GitHub에서 그 커밋 기준으로 원문을 가져온다(사용자의 GitHub 권한으로 요청, 브라우저에 캐시).

## 테이블 요약
| 테이블 | 목적 | 핵심 |
|---|---|---|
| repositories | 분석 대상 저장소 | (owner, name) 유일 |
| analyses | 분석 1회 = 작업 큐의 작업 1개 | (repository_id, commit_sha) 유일 → 같은 커밋은 재사용 |
| code_graphs | 분석 결과 스냅샷 | 큐 조회 시 무거운 그래프를 건드리지 않도록 분리 |
| questions | 출제된 문제 | 규칙/LLM 생성 구분, 직접 검토 후 탈락 기록 |
| attempts | 풀이 기록 | 위치 점수(규칙)와 이유 점수(LLM) 분리, 본인만 접근 |
| human_grades | 사람이 채점한 평가셋 | AI가 쓰지 않음, 주간 백업 |
| llm_calls | LLM 호출 기록 | 비용, 캐시 적중, 모델 비교 수치의 원천 |
| llm_cache | 같은 요청 재사용 | 모델+프롬프트+스키마 버전 해시를 키로 |

## SQL 초안 (D3에 마이그레이션으로 확정)
```sql
create table repositories (
  id          bigint generated always as identity primary key,
  owner       text not null,
  name        text not null,
  created_at  timestamptz not null default now(),
  unique (owner, name)
);

create table analyses (
  id               bigint generated always as identity primary key,
  repository_id    bigint not null references repositories(id) on delete cascade,
  commit_sha       text not null,
  language         text not null default 'python',
  status           text not null default 'queued'
                   check (status in ('queued', 'running', 'done', 'failed')),
  lease_expires_at timestamptz,
  attempts         int not null default 0,
  error_code       text,
  stage_timings    jsonb not null default '{}'::jsonb,
  file_count       int,
  last_opened_at   timestamptz not null default now(),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (repository_id, commit_sha)
);
create index analyses_queue_idx on analyses (created_at)
  where status in ('queued', 'running');

create table code_graphs (
  analysis_id    bigint primary key references analyses(id) on delete cascade,
  schema_version int not null,
  graph          jsonb not null,
  module_index   jsonb not null,
  size_bytes     int not null,
  created_at     timestamptz not null default now()
);

create table questions (
  id               bigint generated always as identity primary key,
  analysis_id      bigint not null references analyses(id) on delete cascade,
  type             text not null check (type in ('impact', 'feature_location')),
  target_node_id   text not null,
  prompt           text not null,
  answer_node_ids  text[] not null,
  rationale        text,
  generated_by     text not null check (generated_by in ('rule', 'llm')),
  status           text not null default 'active' check (status in ('active', 'rejected')),
  created_at       timestamptz not null default now()
);
create index questions_analysis_type_idx on questions (analysis_id, type);

create table attempts (
  id                 bigint generated always as identity primary key,
  user_id            uuid not null references auth.users(id) on delete cascade,
  question_id        bigint not null references questions(id) on delete cascade,
  selected_node_ids  text[] not null,
  reason             text,
  location_score     numeric(4,3),
  reason_score       numeric(4,3),
  feedback           jsonb,
  created_at         timestamptz not null default now()
);
create index attempts_user_created_idx on attempts (user_id, created_at desc);
alter table attempts enable row level security;
create policy attempts_owner on attempts
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create table human_grades (
  id            bigint generated always as identity primary key,
  attempt_id    bigint not null unique references attempts(id) on delete cascade,
  reason_score  numeric(4,3) not null,
  notes         text,
  created_at    timestamptz not null default now()
);

create table llm_calls (
  id             bigint generated always as identity primary key,
  purpose        text not null,
  model          text not null,
  prompt_hash    text not null,
  input_tokens   int,
  cached_tokens  int,
  output_tokens  int,
  cost_usd       numeric(10,6),
  latency_ms     int,
  status         text not null,
  created_at     timestamptz not null default now()
);
create index llm_calls_purpose_created_idx on llm_calls (purpose, created_at);

create table llm_cache (
  key         text primary key,
  response    jsonb not null,
  created_at  timestamptz not null default now(),
  expires_at  timestamptz
);
```
`updated_at`은 애플리케이션에서 갱신하거나 트리거로 처리한다(D3에 결정).

## 작업 큐: 작업 가져오기
```sql
update analyses
set status = 'running',
    attempts = attempts + 1,
    lease_expires_at = now() + interval '10 minutes',
    updated_at = now()
where id = (
  select id from analyses
  where attempts < 3
    and (status = 'queued'
         or (status = 'running' and lease_expires_at < now()))
  order by created_at
  for update skip locked
  limit 1
)
returning *;
```
- 서버가 중간에 꺼져도 임대 시간이 지나면 다른 작업자가 다시 가져간다.
- 시도 3회를 넘긴 작업은 별도 처리로 `failed`로 바꾼다.
- 임대 시간(10분)은 실제 분석 시간을 측정한 뒤 조정한다.

## 그래프 JSON 형식
노드
| 필드 | 예시 | 용도 |
|---|---|---|
| id | `app/services/feed.py::FeedService.recommend` | 파일 경로 + 전체 이름 |
| kind | module, class, function, method, external | 모양 |
| layer | api, service, repository, model, other | 층 |
| role | api_endpoint, db_model 등 | 인식기 결과 |
| file, span | 파일 경로, 시작·끝 줄 | 코드 뷰어 이동 |
| body_hash | 이름 줄을 뺀 본문의 해시 | 이름 변경 판정 |
| metrics | 줄 수, 메서드 수 | 건물 높이 |

연결: `from, to, kind(import|call|inherit), confidence(exact|inferred)`. 추정 연결은 점선.

## 노드 ID와 이름 변경 판정
- ID는 `{상대경로}::{전체이름}`. 중첩 함수는 바깥 이름까지 포함한다.
- 편집 후 같은 파일에서 노드 하나가 사라지고 하나가 생겼을 때, 종류가 같고 body_hash가 같거나 본문이 충분히 비슷하면 "이름 변경", 아니면 "삭제 + 추가"로 판정한다.
- 이름과 본문을 동시에 크게 바꾸면 "삭제 + 추가"로 보이는 것은 받아들이는 한계다. 화면에 이유를 표시한다.

## 용량 (대략치)
파일 300개 저장소면 노드 수천 개, 그래프 JSON은 수 MB 수준이고 Postgres가 압축해 저장한다.
500MB면 분석 수백 건을 담을 수 있다. 30일 미열람 그래프는 삭제하고, 문제와 풀이 기록은 남긴다.

## 비판 후 반영한 것
- GitHub 요청 제한: 사용자 GitHub 권한으로 요청하고 브라우저에 캐시
- 이름+본문 동시 변경: 한계로 받아들이고 화면에 표시
- 그래프 형식 변경: schema_version이 다르면 변환 없이 재분석
