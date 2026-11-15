---
id: D-{{DATE}}-01
type: decision
title: 지식 베이스를 task-workflow 초안으로 시작한다
date: {{DATE_ISO}}
scope: me
domain: common
status: active
source: memo
session: -
range: -
omitted: []
memo: -
supersedes:
superseded_by:
tags: [knowledge-base, bootstrap]
related: []
---

# 지식 베이스를 task-workflow 초안으로 시작한다

## 있었던 일
{{DATE_ISO}}에 setup-knowledge-base 스킬로 이 지식 베이스를 만들었다. 빈 폴더에서 시작하지 않고 task-workflow 플러그인의 초안을 복사했다.
세션 기록에서 뽑은 글이 아니라 스킬이 넣은 글이다. 그래서 `source: memo`이고 뽑은 글 표시가 없다.

## 요지

### 결정
폴더 구조(원본 `raw/`, 요약 문서 `wiki/`)를 초안 그대로 받아들인다. 기록을 쓰는 규칙과 틀, 일하는 규칙은 플러그인 스킬에 있는 것을 따른다. 지식 베이스에는 규칙을 두지 않는다.

### 이유
- 플러그인의 기록 쓰기(`write-records`), 사서(`librarian`), 자가 발전(`analyze-context`) 스킬이 이 구조를 전제로 움직인다. 규칙을 플러그인에 두면 지식 베이스에는 기록만 남아 읽기 쉽다.
- 규칙은 기록이 쌓인 뒤 자가 발전이 사례를 근거로 스킬이나 전역 지침에 넣는다. 처음부터 규칙을 정해 두지 않는다.

### 버린 선택지
빈 폴더에서 시작하기. 스킬이 기대는 폴더와 요약 문서를 하나씩 손으로 만들어야 해서 버렸다.
