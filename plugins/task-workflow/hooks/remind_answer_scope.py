#!/usr/bin/env python3
"""사용자 입력에 질문이 있으면 "물은 것만 답한다"는 규칙이 있는 곳을 알려 준다.

UserPromptSubmit 훅이다. 표준 입력으로 받은 JSON의 prompt에 질문이 있으면
알림 한 줄을 표준 출력에 쓴다. Claude Code는 이 출력을 그 입력 옆에 맥락으로 붙인다.
질문이 없으면 아무것도 쓰지 않는다.

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

REMINDER = (
    "이 입력에는 질문이 들어 있다. "
    "이 사용자는 질문에 물은 것만 답하기를 바란다. "
    "묻지 않은 정보를 언제 덧붙여도 되는지는 응답 양식 \"설명 순서\" 절과 "
    "전역 지침 \"보고\" 절에 적혀 있다."
)


def main():
    try:
        prompt = json.load(sys.stdin).get("prompt", "")
        if isinstance(prompt, str) and QUESTION.search(prompt):
            print(REMINDER)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
