# 색인

무엇이 어디 있는지 적어 둔 지도. 폴더를 뒤질 수 없는 환경에서는 여기서 시작한다.

## 찾는 것 → 위치

| 찾는 것 | 위치 |
| :- | :- |
| 모든 작업에 적용하는 기준 | `wiki/criteria/common.md` |
| 도메인 기준 | `wiki/criteria/<domain>.md` (있을 때) |
| 도메인별 내 맥락(도구, 일, 생활, 취향 등) | `raw/context/` 의 `status: active` 기록. 머리말 `domain`으로 가른다 |
| 예전 결정과 그 이유 | `raw/decisions/` |
| 기준이 생긴 이유 | 그 기준의 "출처"가 가리키는 `raw/cases/` 또는 `raw/decisions/` 기록 |
| 프로젝트마다 어디까지 왔나 | `wiki/board.md` (상황판) |
| 프로젝트가 뭐고 어디 있나 | `wiki/projects/<slug>.md` (프로젝트 카드) |
| 오늘 메모 | `raw/journal/<오늘 날짜>.md` |
| 이 저장소가 답해야 하는 질문 | `tests/regression.md` |
| 코드 저장소가 없는 작업의 산출물 | `work/<작업>/` |

## 폴더

- `raw/cases/` 실수 사례. 사용자 피드백 한 건이 한 파일
- `raw/decisions/` 결정과 이유
- `raw/context/` 나에 대한 맥락. 상황, 제약, 선호, 생활
- `raw/journal/` 날짜별 메모
- `wiki/criteria/` 기준. 공통 하나, 도메인별 하나씩
- `wiki/projects/` 프로젝트 카드. 프로젝트마다 한 장
- `wiki/board.md` 상황판. 프로젝트마다 묶음 하나
- `work/` 코드 저장소가 없는 작업의 산출물. 작업마다 폴더 하나
- `tests/regression.md` 회귀 질문

## 도메인 목록

도메인은 기록이 속한 영역 이름이다. 기준 파일(`wiki/criteria/<domain>.md`)과 머리말의 `domain` 값이 이 이름으로 이어진다.

- `common` 모든 작업에 적용. 기준은 `wiki/criteria/common.md`
- `tools` 맥락용. 내가 쓰는 도구와 환경
- `work` 맥락용. 일과 목표
- `life` 맥락용. 일정, 생활, 취향

작업 도메인(기획, 개발 등)은 아직 없다.
