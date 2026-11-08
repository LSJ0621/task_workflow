# 색인

상황별로 어디를 열지 적어 둔 파일. 폴더를 뒤질 수 없는 환경(MCP로 읽는 경우)에서는 여기서 시작한다.

## 상황 → 열 파일

| 상황 | 연다 |
| :- | :- |
| 작업을 시작한다 | `wiki/criteria/common.md`, 해당 도메인이 있으면 `wiki/criteria/<domain>.md` |
| 나(사용자)에 대해 알아야 한다 | `raw/context/` 의 `status: active` 기록들 |
| 어떤 기준이 왜 생겼는지 알아야 한다 | 그 기준이 가리키는 `raw/cases/` 또는 `raw/decisions/` 기록 |
| 예전에 비슷한 결정을 했는지 확인한다 | `raw/decisions/` 의 제목과 태그 |
| 새 비서 세션이 시작한다 | `wiki/board.md`, 오늘의 `raw/journal/` |
| 내 프로젝트들이 지금 어떤 상태인지 알아야 한다 | `wiki/projects/` 카드들 |
| 검수를 한다 | `wiki/templates/review.md` 틀로 결과를 쓰고 `raw/reviews/`에 둔다 |
| 사용자가 고치거나, 정하거나, 사용자에 대해 알게 됐다 | `raw/journal/오늘.md`에 한 줄. 형식은 `wiki/conventions.md` 메모 절 |
| 뭔가를 정했다 | `wiki/templates/decision.md` 틀로 `raw/decisions/`에 추가한다 |
| 기록 형식이나 식별자가 헷갈린다 | `wiki/conventions.md` |
| 리팩토링을 끝냈다 | `README.md` 불변 조건, `tests/regression.md` |

## 폴더

- `raw/cases/` 실수 사례. 사용자 피드백 한 건이 한 파일
- `raw/decisions/` 결정과 이유
- `raw/context/` 나에 대한 맥락. 상황, 제약, 선호, 생활
- `raw/reviews/` 검수 결과
- `raw/journal/` 날짜별 메모. 사서가 밤에 정식 기록으로 옮김
- `wiki/criteria/` 기준. 공통 하나, 도메인별 하나씩
- `wiki/templates/` 기록 틀
- `wiki/projects/` 프로젝트 카드. 프로젝트마다 한 장
- `wiki/board.md` 진행판. 비서가 갱신
- `work/` 코드 저장소가 없는 작업의 산출물. 작업마다 폴더 하나, PR로 올림
- `wiki/conventions.md` 머리말, 파일명, 식별자, 승격 절차
- `tests/regression.md` 회귀 질문

## 도메인 목록

머리말의 `domain`에는 이 목록의 이름만 쓴다. 새 도메인은 여기에 먼저 추가한다.

- `common` 모든 작업에 적용. 기준은 `wiki/criteria/common.md`
- `tools` 맥락용. 내가 쓰는 도구와 환경
- `work` 맥락용. 일과 목표
- `life` 맥락용. 일정과 생활

작업 도메인(기획, 개발 등)은 아직 없다. 실제 작업을 서너 번 돌린 뒤 `wiki/criteria/<domain>.md`가 생길 때 여기에 추가한다.
