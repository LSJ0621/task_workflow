---
id: D-{{DATE}}-01
type: decision
title: 지식 베이스를 task-workflow 초안으로 시작한다
date: {{DATE_ISO}}
scope: me
domain: common
status: active
supersedes:
superseded_by:
tags: [knowledge-base, bootstrap]
related: []
---

# 지식 베이스를 task-workflow 초안으로 시작한다

## 정해야 했던 것
개인 지식 베이스를 어떤 구조로 시작할지.

## 선택지
- A: 빈 폴더에서 시작
- B: task-workflow 플러그인의 초안으로 시작

## 결정
B. 폴더 구조(원본 `raw/`, 요약 문서 `wiki/`)를 초안 그대로 받아들인다. 기록 규칙과 틀, 일하는 규칙은 플러그인 스킬에 있는 것을 따른다. 지식 베이스에는 규칙을 두지 않는다.

## 이유
- 플러그인의 사서(`librarian`)와 자가 발전(`analyze-context`) 스킬이 이 구조를 전제로 움직인다. 규칙을 플러그인에 두면 지식 베이스에는 기록만 남아 읽기 쉽다.
- 규칙은 기록이 쌓인 뒤 자가 발전이 사례를 근거로 스킬이나 전역 지침에 넣는다. 처음부터 규칙을 정해 두지 않는다.

## 다시 볼 조건
초안의 폴더 구조가 내 기록 방식과 안 맞는 게 드러나면 구조 점검에서 고친다. 초안 자체를 바꿀 필요는 없다.

## 출처
{{DATE_ISO}} setup-knowledge-base 스킬로 생성.
