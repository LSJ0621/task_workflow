---
id: D-YYYYMMDD-NN
type: decision
title:
date: YYYY-MM-DD
scope: me             # me | project:<이름>
domain: common
status: draft          # draft(확인 전) | active | superseded
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

### 결정
뭘 골랐나. 한 문장. "있었던 일"에 있는 것만 가지고 쓴다.

### 이유
왜 그걸 골랐나. "있었던 일"에 없으면 "미확인". 지어내지 않는다.

### 버린 선택지
버린 쪽과 버린 이유. 없으면 "미확인".

---

틀을 쓰는 법 (기록 파일에는 이 아래를 넣지 않는다)

- `source: memo`면 `## 있었던 일`에 메모의 있었던 일과 `사용자 말:`을 그대로 옮기고 표시 두 줄은 두지 않는다. `session: -`, `range: -`.
- 결정에는 `## 분석` 절이 없다.
- 예전 기록의 일부만 바꾸는 결정이면 `### 결정` 끝에 "예전 기록 <id>의 이 부분을 바꾼다"고 한 줄 적는다.

## 예시 (가상, 형식 참고용)

```markdown
---
id: D-20250103-01
type: decision
title: 주간 보고를 금요일 오후에 받는다
date: 2025-01-03
scope: me
domain: common
status: draft
source: session
session: 3f2a9c1e-0b7d-4e55-9a10-6c2d8e4f1b73
range: 1a2b3c4d-0e1f-4a2b-8c3d-4e5f6a7b8c9d..9f8e7d6c-5b4a-4c3d-9e2f-1a0b9c8d7e6f
omitted: []
memo: 2025-01-03 16:40
supersedes:
superseded_by:
tags: []
related: []
---

# 주간 보고를 금요일 오후에 받는다

## 있었던 일
<!-- extract:start -->
**에이전트** (16:31)
> 주간 보고를 월요일 아침에 드릴까요, 금요일 오후에 드릴까요?

**사용자** (16:33)
> 금요일 오후로 해. 월요일 아침엔 회의가 있어서 못 봐

**에이전트** (16:34)
> 금요일 오후로 정했습니다.
<!-- extract:end -->

## 요지

### 결정
주간 보고는 금요일 오후에 받는다.

### 이유
월요일 아침에는 회의가 있어서 보고를 볼 수 없다.

### 버린 선택지
월요일 아침. 회의와 겹친다.
```
