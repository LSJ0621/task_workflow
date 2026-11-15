---
id: C-YYYYMMDD-NN
type: case
title:
date: YYYY-MM-DD
scope: me             # me | project:<이름>
domain:
status: draft          # draft(확인 전) | active | superseded
source: session        # session(스크립트가 세션 기록에서 뽑음) | memo(메모에서 옮김. 세션 기록을 못 찾았거나 예전 기록)
session:               # 세션 id. 없으면 -
range:                 # <첫 줄 uuid>..<끝 줄 uuid>. 없으면 -
omitted: []            # 비밀값 때문에 뺀 줄의 uuid
memo: YYYY-MM-DD HH:MM # 이 기록이 나온 메모 줄
supersedes:
superseded_by:
tags: []              # 사용자가 지적을 거뒀으면 retracted, 못 찾은 것이면 notfound
related: []           # 관련 C-, D-, X- id
---

# <제목>

## 있었던 일
<!-- extract:start -->
(스크립트 출력. 사람이든 에이전트든 손으로 고치지 않는다)
<!-- extract:end -->

## 요지

### 어떤 작업에서
작업 설명 한 줄. 모든 프로젝트에 걸리는 사례면 일의 종류(화면 만들기, 커밋, 설명하기 같은 것)도 적는다.

### 에이전트가 한 것
한두 문장. 판단 없이 사실만. "있었던 일"에 있는 것만 가지고 쓴다.

## 분석
아직 없음

### 메모의 풀이
메모의 `풀이:`를 그대로 옮긴다. 에이전트의 추정이고 사용자가 한 말이 아니다. 메모에 풀이가 없으면 이 절을 두지 않는다.

---

틀을 쓰는 법 (기록 파일에는 이 아래를 넣지 않는다)

- 제목은 에이전트가 한 일로 적는다.
- `source: memo`면 `## 있었던 일`에 메모의 있었던 일과 `사용자 말:`을 그대로 옮기고 표시 두 줄은 두지 않는다. `session: -`, `range: -`.
- `notfound` 사례는 `## 요지`에 `### 어떤 작업에서`와 `### 에이전트가 한 것` 대신 `### 찾던 것`과 `### 찾아본 곳`을 쓴다. 머리말 `tags`에 `notfound`.
- `## 분석`은 3단계(`analyze-context`)가 "아직 없음"을 지우고 `### 원인 추정`, `### 근거`, `### 관련 규칙`을 채운다. `### 메모의 풀이`는 그 아래에 그대로 둔다.

## 예시 (가상, 형식 참고용)

```markdown
---
id: C-20250102-01
type: case
title: 환경 변수 파일을 gitignore에 넣지 않고 커밋했다
date: 2025-01-02
scope: me
domain: common
status: draft
source: session
session: 3f2a9c1e-0b7d-4e55-9a10-6c2d8e4f1b73
range: 7b1d0c2a-5e4f-4a88-b3c1-2f9e6d0a1c44..e09a3f5b-1c2d-4b7e-8f60-9d4c2a7b5e13
omitted: []
memo: 2025-01-02 14:20
supersedes:
superseded_by:
tags: []
related: []
---

# 환경 변수 파일을 gitignore에 넣지 않고 커밋했다

## 있었던 일
<!-- extract:start -->
**사용자** (14:05)
> 새 프로젝트 초기 설정 해 줘

**도구** (14:06)
- Write: example-app/.env
- Write: example-app/README.md
- Bash: 초기 설정 파일을 커밋한다

**에이전트** (14:07)
> 초기 설정을 끝내고 커밋했습니다.

**사용자** (14:15)
> 환경 변수 파일이 올라갔잖아. 이거 하나만 막을 게 아니라 비밀값은 공개된 데 나가면 안 되는 거야

**에이전트** (14:16)
> 환경 변수 파일을 gitignore에 넣고 커밋에서 뺐습니다.
<!-- extract:end -->

## 요지

### 어떤 작업에서
새 프로젝트 초기 설정. 일의 종류는 커밋.

### 에이전트가 한 것
환경 변수 파일을 만들고 gitignore에 넣지 않은 채 다른 설정 파일과 함께 커밋했다.

## 분석
아직 없음

### 메모의 풀이
환경 변수 파일만이 아니라 비밀값이 든 파일은 무엇이든 커밋 전에 걸러야 한다
```

`notfound` 사례의 본문 예시:

```markdown
# 배포 요일을 지식 베이스에서 찾지 못했다

## 있었던 일
<!-- extract:start -->
**사용자** (10:31)
> 이번 주 배포 준비해 줘

**도구** (10:32)
- Read: INDEX.md
- Read: wiki/context.md
- Read: wiki/projects/budget-app.md

**에이전트** (10:34)
> 배포 요일이 지식 베이스에 안 보입니다. 어느 요일에 배포할까요?
<!-- extract:end -->

## 요지

### 찾던 것
앱을 어느 요일에 배포하기로 했는지.

### 찾아본 곳
색인, 맥락 요약, 프로젝트 카드.

## 분석
아직 없음
```
