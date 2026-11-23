---
id: X-YYYYMMDD-NN
type: context
title:
date: YYYY-MM-DD
scope: me             # me | project:<이름>
domain: life          # work(일·목표) | life(일정·생활) | taste(소통 방식·선호·성향) | tools(기기·구독·실행 환경)
status: draft          # draft(확인 전) | active | superseded | archived
source: session        # session(스크립트가 세션 기록에서 뽑음) | memo(메모에서 옮김. 세션 기록을 못 찾았거나 예전 기록)
session:               # 세션 id. 없으면 -
range:                 # <첫 줄 uuid>..<끝 줄 uuid>. 없으면 -
omitted: []            # 비밀값 때문에 뺀 줄의 uuid
memo: YYYY-MM-DD HH:MM # 이 기록이 나온 메모 줄
supersedes:
superseded_by:
tags: []
related: []
---

# <제목>

## 있었던 일
<!-- extract:start -->
(스크립트 출력. 사람이든 에이전트든 손으로 고치지 않는다)
<!-- extract:end -->

## 요지

### 사실
나에 대한 사실, 선호, 상황, 제약. 한 기록에 한 가지. 오래 맞는 사실만 쓴다. "있었던 일"에 있는 것만 가지고 쓴다. 그날의 상태(작업이 어디까지 됐나)는 맥락이 아니라 상황판에 둔다.

### 유효 기간
언제까지 맞는 말인가. "있었던 일"에 없으면 "변할 수 있음".

---

틀을 쓰는 법 (기록 파일에는 이 아래를 넣지 않는다)

- `source: memo`면 `## 있었던 일`에 메모의 있었던 일과 `사용자 말:`을 그대로 옮기고 표시 두 줄은 두지 않는다. `session: -`, `range: -`.
- 맥락에는 `## 분석` 절이 없다.
- 예전 기록의 일부만 바꾸는 맥락이면 `### 사실` 끝에 "예전 기록 <id>의 이 부분을 바꾼다"고 한 줄 적는다.

## 예시 (가상, 형식 참고용)

```markdown
---
id: X-20250104-01
type: context
title: 평일 저녁 여덟 시 뒤에만 개인 프로젝트를 한다
date: 2025-01-04
scope: me
domain: life
status: draft
source: session
session: 3f2a9c1e-0b7d-4e55-9a10-6c2d8e4f1b73
range: 2c4e6a8b-1d3f-4b5a-9c7e-0f2a4c6e8b1d..5d7f9b1c-3e5a-4c7e-8b0d-2f4a6c8e0b3d
omitted: []
memo: 2025-01-04 20:15
supersedes:
superseded_by:
tags: []
related: []
---

# 평일 저녁 여덟 시 뒤에만 개인 프로젝트를 한다

## 있었던 일
<!-- extract:start -->
**에이전트** (20:02)
> 내일 오후 세 시에 이어서 할까요?

**사용자** (20:04)
> 평일 낮엔 회사라 안 돼. 저녁 여덟 시 넘어서만 할 수 있어. 이번 분기까지는 그래

**에이전트** (20:05)
> 내일 저녁 여덟 시 뒤로 잡겠습니다.
<!-- extract:end -->

## 요지

### 사실
평일 낮에는 회사 일을 해서 개인 프로젝트는 저녁 여덟 시 뒤에만 한다.

### 유효 기간
이번 분기까지.
```
