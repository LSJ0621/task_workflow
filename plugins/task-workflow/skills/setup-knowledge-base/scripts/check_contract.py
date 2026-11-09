#!/usr/bin/env python3
"""지식 베이스가 플러그인이 기대하는 두 가지 계약을 지키는지 점검한다.

사용: check_contract.py <지식 베이스 폴더>
종료 코드 0 = 두 가지 모두 통과. 1 = 하나라도 실패.
필수: 색인(INDEX.md), 메모 위치(raw/journal/).
권장 항목(지식 베이스 안내 CLAUDE.md, 상황판 wiki/board.md, 규칙별 사례표 wiki/rule-cases.md, git 저장소)은 실패로 치지 않는다.
규칙과 틀은 플러그인 스킬 안에 있으므로 지식 베이스에 규칙 문서는 두지 않는다.
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
    ]
    recommended = [
        ("지식 베이스 안내", (kb / "CLAUDE.md").exists(), "CLAUDE.md"),
        ("상황판", (kb / "wiki" / "board.md").exists(), "wiki/board.md"),
        ("규칙별 사례표", (kb / "wiki" / "rule-cases.md").exists(), "wiki/rule-cases.md"),
        ("git 저장소", is_git(kb), "git init"),
    ]
    # 권장 항목이 있어도 지금 초안과 모양이 다르면 경고만 한다. 실패로 치지 않는다.
    shape = [
        ("지식 베이스 안내", kb / "CLAUDE.md", "task-workflow:librarian",
         "기록은 task-workflow:librarian 을 따른다는 안내가 없다"),
        ("상황판", kb / "wiki" / "board.md", "고친 날짜",
         "프로젝트 묶음 형식(어디까지·다음 할 일·막힌 것·고친 날짜)이 아니다"),
        ("규칙별 사례표", kb / "wiki" / "rule-cases.md", "| 사례 | 한 줄 요약 | 관련 규칙 | 거스름 |",
         "표 머리가 | 사례 | 한 줄 요약 | 관련 규칙 | 거스름 | 이 아니다"),
    ]
    ok = True
    print(f"점검 대상: {kb}")
    for name, passed, hint in required:
        print(f"  [{'통과' if passed else '실패'}] 필수 · {name}" + ("" if passed else f" — {hint}"))
        ok = ok and passed
    for name, passed, path in recommended:
        print(f"  [{'있음' if passed else '없음'}] 권장 · {name} ({path})")
    for name, path, needle, msg in shape:
        if path.is_file() and needle not in path.read_text(encoding="utf-8"):
            print(f"  [경고] 권장 · {name} — {msg}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
