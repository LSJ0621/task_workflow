# 색인

무엇이 어디 있는지 적어 둔 지도. 폴더를 뒤질 수 없는 환경(MCP로 읽는 경우)에서는 여기서 시작한다.
기록을 쓰는 규칙과 틀은 이 저장소에 없고 `task-workflow-assistant` 플러그인의 스킬에 있다.

## 찾는 것 → 위치

| 찾는 것 | 위치 |
| :- | :- |
| 모든 작업에 적용하는 기준 | `wiki/criteria/common.md` |
| 도메인 기준 | `wiki/criteria/<domain>.md` (있을 때) |
| 나(사용자)에 대한 맥락 | `raw/context/` 의 `status: active` 기록 |
| 기준이 생긴 이유 | 그 기준의 "출처"가 가리키는 `raw/cases/` 또는 `raw/decisions/` 기록 |
| 예전 결정과 그 이유 | `raw/decisions/` |
| 지금 돌아가는 작업 | `wiki/board.md` |
| 오늘 메모 | `raw/journal/<오늘 날짜>.md` |
| 프로젝트 상태 | `wiki/projects/` |
| 검수 결과 | `raw/reviews/` |
| 팀장 보고서 | `raw/reports/` |

## 폴더

- `raw/cases/` 실수 사례. 사용자 피드백 한 건이 한 파일
- `raw/decisions/` 결정과 이유
- `raw/context/` 나에 대한 맥락. 상황, 제약, 선호, 생활
- `raw/reviews/` 검수 결과
- `raw/reports/` 팀장 보고서
- `raw/journal/` 날짜별 메모
- `wiki/criteria/` 기준. 공통 하나, 도메인별 하나씩
- `wiki/projects/` 프로젝트 카드. 프로젝트마다 한 장
- `wiki/board.md` 진행판
- `work/` 코드 저장소가 없는 작업의 산출물. 작업마다 폴더 하나
- `tests/regression.md` 이 저장소가 답해야 하는 질문 목록

## 도메인 목록

도메인은 기록이 속한 영역 이름이다. 기준 파일(`wiki/criteria/<domain>.md`)과 머리말의 `domain` 값이 이 이름으로 이어진다.

- `common` 모든 작업에 적용. 기준은 `wiki/criteria/common.md`
- `tools` 맥락용. 내가 쓰는 도구와 환경
- `work` 맥락용. 일과 목표
- `life` 맥락용. 일정과 생활

작업 도메인(기획, 개발 등)은 아직 없다.
