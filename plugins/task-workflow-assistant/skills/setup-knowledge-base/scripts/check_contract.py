#!/usr/bin/env python3
"""지식 베이스가 플러그인이 기대하는 네 가지 계약을 지키는지 점검한다.

사용: check_contract.py <지식 베이스 폴더>
종료 코드 0 = 네 가지 모두 통과. 1 = 하나라도 실패. 권장 항목(클라우드 권한 파일, 비서용 CLAUDE.md)은 실패로 치지 않는다.
"""
import pathlib, re, sys

def main():
    if len(sys.argv) < 2:
        sys.exit("사용: check_contract.py <지식 베이스 폴더>")
    kb = pathlib.Path(sys.argv[1]).expanduser().resolve()
    conv = kb / "wiki" / "conventions.md"
    conv_text = conv.read_text(encoding="utf-8") if conv.exists() else ""
    readme = kb / "README.md"
    readme_text = readme.read_text(encoding="utf-8") if readme.exists() else ""

    required = [
        ("규칙 문서", conv.exists() and all(k in conv_text for k in ["식별자", "머리말"]),
         "wiki/conventions.md 에 식별자·머리말 규칙이 있어야 한다"),
        ("색인", (kb / "INDEX.md").exists(), "INDEX.md 가 있어야 한다"),
        ("불변 조건", "불변 조건" in readme_text, "README.md 에 '불변 조건' 절이 있어야 한다"),
        ("메모 위치", bool(re.search(r"journal|메모", conv_text)), "wiki/conventions.md 에 메모 위치가 적혀 있어야 한다"),
    ]
    recommended = [
        ("클라우드 세션 권한", (kb / ".claude" / "settings.json").exists(), ".claude/settings.json"),
        ("비서용 CLAUDE.md", (kb / "CLAUDE.md").exists(), "CLAUDE.md"),
        ("진행판", (kb / "wiki" / "board.md").exists(), "wiki/board.md"),
    ]
    ok = True
    print(f"점검 대상: {kb}")
    for name, passed, hint in required:
        print(f"  [{'통과' if passed else '실패'}] 필수 · {name}" + ("" if passed else f" — {hint}"))
        ok = ok and passed
    for name, passed, path in recommended:
        print(f"  [{'있음' if passed else '없음'}] 권장 · {name} ({path})")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
