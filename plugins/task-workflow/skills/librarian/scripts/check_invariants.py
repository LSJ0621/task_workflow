#!/usr/bin/env python3
"""지식 베이스의 불변 조건을 점검한다. 사용: check_invariants.py <지식 베이스>
종료 코드 0 = 통과. 점검: 식별자 중복 없음, 모든 원본에 id·date·status 머리말, 결정에 이유 절,
본문의 모든 C-·D-·X-·R- id 참조가 존재, superseded 쌍 일관,
규칙별 사례표(wiki/rule-cases.md)가 있으면 모든 사례가 표에 있음.
P-로 시작하는 옛 기준 항목 id는 없어진 기준 문서의 이름이라 지난 기록에 남아 있어도 점검하지 않는다."""
import pathlib, re, sys

ID_RE = re.compile(r"\b([CDXR]-\d{8}-\d{2})\b")

def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1); fm[k.strip()] = v.split("#")[0].strip()
    return fm

def main():
    if len(sys.argv) < 2:
        sys.exit("사용: check_invariants.py <지식 베이스>")
    kb = pathlib.Path(sys.argv[1]).expanduser()
    problems = []
    ids = {}
    case_ids = set()
    raw_files = [p for p in kb.glob("raw/**/*.md") if "journal" not in p.parts]
    for p in raw_files:
        text = p.read_text(encoding="utf-8")
        fm = frontmatter(text)
        for k in ("id", "date", "status"):
            if not fm.get(k):
                problems.append(f"머리말 {k} 없음: {p.relative_to(kb)}")
        i = fm.get("id")
        if i:
            if i in ids: problems.append(f"식별자 중복: {i} ({p.name}, {ids[i]})")
            ids[i] = p.name
            if not p.name.startswith(i): problems.append(f"파일명이 id로 시작하지 않음: {p.name}")
            if fm.get("type") == "case": case_ids.add(i)
        if fm.get("type") == "decision" and "## 이유" not in text:
            problems.append(f"결정에 이유 절 없음: {p.name}")
        if fm.get("status") == "superseded" and not fm.get("superseded_by"):
            problems.append(f"superseded 인데 superseded_by 없음: {p.name}")
    # 메모는 정식 기록 전 재료라 id 참조 점검에서 뺀다. 숨김 폴더(.git, .claude 등)도 뺀다.
    skip = {"journal"}
    for p in kb.glob("**/*.md"):
        rel = p.relative_to(kb).parts
        if any(x.startswith(".") for x in rel) or skip & set(rel): continue
        body = p.read_text(encoding="utf-8")
        for ref in set(ID_RE.findall(body)):
            if ref not in ids:
                problems.append(f"없는 id 참조 {ref}: {p.relative_to(kb)}")
    table = kb / "wiki" / "rule-cases.md"
    rows = 0
    if table.is_file():
        listed = set()
        for line in table.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\|\s*(C-\d{8}-\d{2})\s*\|", line)
            if m:
                listed.add(m.group(1)); rows += 1
        for c in sorted(case_ids - listed):
            problems.append(f"규칙별 사례표에 없는 사례: {c}")
    print(f"점검 대상: {kb} · 원본 {len(raw_files)}개, 규칙별 사례표 "
          + (f"{rows}줄" if table.is_file() else "없음"))
    for x in problems: print("  [문제]", x)
    print("  통과" if not problems else f"  문제 {len(problems)}건")
    sys.exit(0 if not problems else 1)

if __name__ == "__main__":
    main()
