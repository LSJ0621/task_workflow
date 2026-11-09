#!/usr/bin/env python3
"""지식 베이스가 플러그인이 기대하는 세 가지 계약을 지키는지 점검한다.

사용: check_contract.py <지식 베이스 폴더>
종료 코드 0 = 세 가지 모두 통과. 1 = 하나라도 실패.
필수: 색인(INDEX.md), 메모 위치(raw/journal/), 기준 문서 위치(wiki/criteria/common.md).
권장 항목(비서 지시 CLAUDE.md, 진행판, git 저장소)은 실패로 치지 않는다.
규칙과 틀은 플러그인 스킬 안에 있으므로 지식 베이스에 규칙 문서가 있을 필요는 없다.
"""
import pathlib, subprocess, sys

def is_git(kb):
    try:
        r = subprocess.run(["git", "-C", str(kb), "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except OSError:
        return False

def main():
    if len(sys.argv) < 2:
        sys.exit("사용: check_contract.py <지식 베이스 폴더>")
    kb = pathlib.Path(sys.argv[1]).expanduser().resolve()

    required = [
        ("색인", (kb / "INDEX.md").is_file(), "INDEX.md 가 있어야 한다"),
        ("메모 위치", (kb / "raw" / "journal").is_dir(), "raw/journal/ 폴더가 있어야 한다"),
        ("기준 문서 위치", (kb / "wiki" / "criteria" / "common.md").is_file(),
         "wiki/criteria/common.md 가 있어야 한다"),
    ]
    recommended = [
        ("비서 지시", (kb / "CLAUDE.md").exists(), "CLAUDE.md"),
        ("진행판", (kb / "wiki" / "board.md").exists(), "wiki/board.md"),
        ("git 저장소", is_git(kb), "git init"),
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
