#!/usr/bin/env python3
"""지금 유효한(status: active) 결정과 맥락을 한 줄씩 찍는다.

사용: list_active.py [<지식 베이스>] [--scope me|project:<이름> ...] [--type decision|context]
출력: 기록마다 `id | 제목 | 요지 첫 줄` 한 줄. id 순서다. 맞는 기록이 없으면 아무것도 찍지 않는다. 종료 코드 0.
지식 베이스를 안 주면 $KNOWLEDGE_BASE_DIR 을 쓴다.
--scope 는 여러 개 줄 수 있다. 안 주면 모든 범위다. --type 을 안 주면 결정과 맥락 둘 다다.

정리 단계가 새로 확정된 결정을 지금 유효한 결정과 대조해, 바뀐 예전 기록에 대체됨 표시를 할 때 쓴다.
기록을 전부 열지 않고 같은 범위의 유효한 기록만 훑어보게 하려는 것이다.

요지 첫 줄은 `## 요지` 아래에서 처음 나오는 글 줄이다(`###` 제목은 건너뛴다).
`## 요지`가 없는 예전 기록은 `## 결정`이나 `## 사실` 아래 첫 줄을 쓴다. 그것도 없으면 `-`다.
그날의 상태 맥락(snapshot: true)은 지금 판단에 쓰지 않으므로 뺀다.
"""
import argparse, os, pathlib, re, sys

SCOPE_RE = re.compile(r"^(me|project:[A-Za-z0-9][A-Za-z0-9._-]*)$")
FOLDERS = {"decision": "raw/decisions", "context": "raw/context"}
SUMMARY_HEADS = ("## 요지", "## 결정", "## 사실")   # 새 틀, 예전 결정, 예전 맥락

def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1); fm[k.strip()] = v.split(" #")[0].strip()
    return fm

def first_line_under(text, head):
    lines = text.splitlines()
    for position, line in enumerate(lines):
        if line.strip() != head:
            continue
        for body in lines[position + 1:]:
            if re.match(r"^#{1,2} ", body):
                break   # 다음 절이 시작됐다
            if body.strip() and not body.startswith("#") and not body.startswith("<!--"):
                return body.strip()
    return None

def summary_line(text):
    for head in SUMMARY_HEADS:
        line = first_line_under(text, head)
        if line:
            return line
    return "-"

def title_of(fm, text):
    if fm.get("title"):
        return fm["title"].strip("\"'")
    m = re.search(r"^# (.+)$", text, re.M)
    return m.group(1).strip() if m else "-"

def one_cell(value):
    return " ".join(value.replace("|", "/").split())

def main():
    ap = argparse.ArgumentParser(description="지금 유효한 결정과 맥락을 id | 제목 | 요지 첫 줄로 찍는다")
    ap.add_argument("knowledge_base", nargs="?", default=os.environ.get("KNOWLEDGE_BASE_DIR"))
    ap.add_argument("--scope", nargs="+", action="extend", default=[], metavar="me|project:<이름>")
    ap.add_argument("--type", choices=sorted(FOLDERS), action="append", dest="types")
    a = ap.parse_args()
    if not a.knowledge_base:
        sys.exit("지식 베이스를 모른다. 인자로 주거나 KNOWLEDGE_BASE_DIR 을 둔다")
    kb = pathlib.Path(a.knowledge_base).expanduser()
    if not (kb / "raw").is_dir():
        sys.exit(f"지식 베이스가 아님(raw 없음): {kb}")
    for scope in a.scope:
        if not SCOPE_RE.match(scope):
            sys.exit(f"--scope 값이 me나 project:<이름>이 아님: {scope}")
    rows = []
    for kind in a.types or sorted(FOLDERS):
        for p in sorted((kb / FOLDERS[kind]).glob("*.md")):
            text = p.read_text(encoding="utf-8")
            fm = frontmatter(text)
            if fm.get("status") != "active" or not fm.get("id"):
                continue
            if fm.get("snapshot", "").lower() == "true":
                continue
            if a.scope and fm.get("scope") not in a.scope:
                continue
            rows.append((fm["id"], one_cell(title_of(fm, text)), one_cell(summary_line(text))))
    for row in sorted(rows):
        print(" | ".join(row))

if __name__ == "__main__":
    main()
