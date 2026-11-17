#!/usr/bin/env python3
"""사용자 입력에 질문이 있으면 "물은 것만 답한다"는 규칙이 있는 곳을 알려 준다.

UserPromptSubmit 훅이다. 표준 입력으로 받은 JSON의 prompt에 질문이 있으면
알림 한 줄을 표준 출력에 쓴다. Claude Code는 이 출력을 그 입력 옆에 맥락으로 붙인다.
질문이 없으면 아무것도 쓰지 않는다.

입력이 앞 답의 구절을 인용해 되묻는 것이면 질문 알림 대신 되묻는 입력 알림을 쓴다.
사용자가 방금 읽은 내용이라는 것을 알려 주기 위해서다.

입력을 막지 않는다. 어떤 오류가 나도 조용히 0으로 끝낸다.
종료 코드 2는 사용자 입력을 막으므로 쓰지 않는다.

규칙 자체는 여기에 두지 않는다. 응답 양식 "설명 순서" 절과 전역 지침 "보고" 절에 있다.
"""
import json
import re
import sys

# 물음표 뒤가 공백, 닫는 따옴표·괄호, 입력 끝이면 질문으로 본다.
# 주소의 ?key=value 같은 것은 뒤에 글자가 바로 붙어서 걸리지 않는다.
QUESTION = re.compile(r"[?？](?=\s|$|[\"'”’)\]])")

# 앱에서 답의 한 구절을 골라 답장하면 입력에 이 표시가 붙고 그 아래에 인용한 구절이 온다.
# 표시가 없는 환경에서는 걸리지 않고, 그때는 위의 질문 알림만 나간다.
QUOTED_REPLY = re.compile(r"<!--\s*reply\b")

QUOTED_REMINDER = (
    "이 입력은 앞 답의 구절을 인용해 되묻고 있다. "
    "인용한 내용은 이 사용자가 방금 읽은 것이다. "
    "그 내용과 앞에서 한 설명을 다시 풀지 않고 물은 것의 답만 적는다. "
    "기준은 응답 양식 \"설명 순서\" 절에 적혀 있다."
)

REMINDER = (
    "이 입력에는 질문이 들어 있다. "
    "이 사용자는 질문에 물은 것에 답하기를 바란다. "
    "묻지 않은 것은 덧붙이지 않고, 답을 이해하는 데 필요한 맥락은 빼지 않는다. "
    "무엇을 채우고 무엇을 뺄지의 기준은 응답 양식 \"설명 순서\" 절과 "
    "전역 지침 \"보고\" 절에 적혀 있다."
)


def main():
    try:
        prompt = json.load(sys.stdin).get("prompt", "")
        if not isinstance(prompt, str):
            return 0
        if QUOTED_REPLY.search(prompt):
            print(QUOTED_REMINDER)
        elif QUESTION.search(prompt):
            print(REMINDER)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
