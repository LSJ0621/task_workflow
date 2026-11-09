# 구조 변경 브랜치 머지

지식 베이스의 로컬 브랜치 `proposal/structure-YYYYMMDD`를 main에 들이는 방법이다. 정리 절차 10단계가 파일을 옮기거나 합친 뒤 읽는다.
아래 명령의 `$KB`는 지식 베이스 폴더다. 지식 베이스 체크아웃은 main 그대로 두고 그 자리에서 머지한다. 사용자의 다른 세션이 같은 폴더의 main에 메모를 커밋하고 있을 수 있어서다.

## 묻지 않고 머지한다

파일 이동·합치기·이름 바꾸기는 내용이 바뀌지 않으므로 묻지 않는다. 브랜치를 만든 세션이 커밋을 마치면 바로 머지하고, 보고에 무엇이 어디로 옮겨졌는지 적는다.
그래도 브랜치를 거치는 이유는 머지 커밋 하나로 무엇이 옮겨졌는지 이력에서 가를 수 있어서다. 구조 변경이 아닌 수정을 이 브랜치에 섞지 않는다.

```bash
git -C "$KB" pull --ff-only
git -C "$KB" merge --no-ff --no-edit proposal/structure-YYYYMMDD \
  -m "구조 변경 머지: proposal/structure-YYYYMMDD" -m "<무엇을 어디로 옮겼는지 한 문장>"
git -C "$KB" branch -d proposal/structure-YYYYMMDD
git -C "$KB" push
```

머지가 충돌하면 `git -C "$KB" merge --abort`로 되돌리고 브랜치를 남긴 채 보고에 적는다. 직접 풀지 않는다.

## 머지 뒤

- 카드 갱신은 하지 않는다. 다음 정리가 원본에서 다시 만든다. 두 세션이 같은 파일을 고치면 push가 충돌해서다.
