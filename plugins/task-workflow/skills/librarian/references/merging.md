# 제안 브랜치 머지

지식 베이스의 로컬 브랜치 `proposal/*`를 main에 들이는 방법이다. 사용자와 대화 중인 세션이 사용자의 답을 받았을 때, 그리고 정리 절차 10단계가 구조 변경을 머지할 때 읽는다.
아래 명령의 `$KB`는 지식 베이스 폴더다. 지식 베이스 체크아웃은 main 그대로 두고 그 자리에서 머지한다. 사용자의 다른 세션이 같은 폴더의 main에 메모를 커밋하고 있을 수 있어서다.

## 두 종류는 승인 방법이 다르다

| 브랜치 | 승인 | 누가 머지하나 |
| :- | :- | :- |
| `proposal/criteria-YYYYMMDD` (기준 반영 제안) | 사용자에게 묻고 "머지해"라는 답을 받는다 | 그 답을 받은, 사용자와 대화 중인 세션 |
| `proposal/structure-YYYYMMDD` (구조 변경 제안) | 묻지 않는다 | 그 브랜치를 만든 세션이 바로. 보고에 무엇이 바뀌었는지 적는다 |

기준은 다음 작업의 판단을 바꾸므로 사용자가 정한다. 파일 이동·합치기는 내용이 바뀌지 않으므로 묻지 않는다. 그래도 브랜치를 거치는 이유는 머지 커밋 하나로 무엇이 옮겨졌는지 이력에서 가를 수 있어서다.
두 종류를 한 브랜치에 섞지 않는다.

## 기준 반영 제안

- **알리기.** 사용자가 지식 베이스나 기준을 물을 때, 정리 보고를 전할 때 남은 기준 제안 브랜치를 본다. 커밋 첫 줄이 제안 하나다. 첫 줄을 쉬운 말로 다듬어 "승인 기다리는 기준 제안 n건: …. 머지할까요?"라고 묻는다.
  ```bash
  git -C "$KB" branch --list 'proposal/criteria-*'
  git -C "$KB" log main..proposal/criteria-YYYYMMDD --format='%s'
  ```
- **"머지해".** 이 머지가 승인이고, 승인 기록은 머지 커밋 메시지에 남는다.
  ```bash
  git -C "$KB" pull --ff-only
  git -C "$KB" merge --no-ff --no-edit proposal/criteria-YYYYMMDD \
    -m "제안 머지: proposal/criteria-YYYYMMDD" -m "사용자 승인: \"<사용자 말 그대로>\""
  git -C "$KB" branch -d proposal/criteria-YYYYMMDD
  git -C "$KB" push
  ```
  머지가 충돌하면 `git -C "$KB" merge --abort`로 되돌리고 직접 풀지 않는다. decision 메모 `머지 충돌: proposal/<브랜치>, 사용자: "<말>"`을 남기고 사용자에게 "다음 정리 때 지금 기준 문서에 맞춰 다시 만들어 다시 물어요"라고 알린다.
- **"버려", "안 해".** `git -C "$KB" branch -D proposal/<브랜치>`로 지우고, decision 메모 `기각: proposal/<브랜치> (<사례 id들>), 사용자: "<말>"`을 남긴다. 정리 절차는 이 메모로 기각을 안다. 브랜치가 없어진 것만으로는 기각인지 알 수 없어서다.
- **일부만 승인.** 머지하지 않는다. decision 메모 `부분 승인: proposal/<브랜치>, 승인 <사례 id들>, 사용자: "<말>"`을 남긴다. 다음 정리가 승인된 제안만으로 브랜치를 다시 만들고 다시 묻는다.

## 구조 변경 제안

브랜치를 만든 세션이 커밋을 마치면 바로 머지한다.
```bash
git -C "$KB" pull --ff-only
git -C "$KB" merge --no-ff --no-edit proposal/structure-YYYYMMDD \
  -m "구조 변경 머지: proposal/structure-YYYYMMDD" -m "<무엇을 어디로 옮겼는지 한 문장>"
git -C "$KB" branch -d proposal/structure-YYYYMMDD
git -C "$KB" push
```
머지가 충돌하면 `merge --abort`로 되돌리고 브랜치를 남긴 채 보고에 적는다. 직접 풀지 않는다.

## 머지 뒤

- 사례 승인 표시나 카드 갱신은 하지 않는다. 다음 정리의 11단계가 한다. 두 세션이 같은 파일을 고치면 push가 충돌해서다.
- **스킬 수정 PR은 예외다.** 플러그인은 GitHub 저장소에서 설치해서, 스킬 수정 제안은 플러그인 저장소의 GitHub PR로 온다. 사용자가 "머지해"라고 하면 그 PR을 GitHub에서 머지한다(`gh pr merge`).
