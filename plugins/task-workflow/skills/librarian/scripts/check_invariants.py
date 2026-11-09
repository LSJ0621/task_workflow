#!/usr/bin/env python3
"""지식 베이스의 불변 조건을 점검한다. 사용: check_invariants.py <지식 베이스>
종료 코드 0 = 통과. 점검: 식별자 중복 없음, 모든 원본에 id·date·status 머리말, 결정에 이유 절,
본문의 모든 C-·D-·X-·R- id 참조가 존재, superseded 쌍 일관,
사례·결정·맥락에 scope(me 또는 project:<이름>) 있음(raw/archive/ 아래는 예전 기록이라 건너뜀),
wiki/context.md가 있으면 유효한 결정·맥락 id가 wiki/context.md나 wiki/projects/*.md 어딘가에 있음
(머리말 snapshot: true 인 맥락은 그날의 상태라 건너뜀),
규칙별 사례표(wiki/rule-cases.md)가 있으면 표 머리가 지금 형식이고 모든 사례가 표에 있음.
P-로 시작하는 옛 기준 항목 id는 없어진 기준 문서의 이름이라 지난 기록에 남아 있어도 점검하지 않는다."""
import pathlib, re, sys

ID_RE = re.compile(r"\b([CDXR]-\d{8}-\d{2})\b")
SCOPE_RE = re.compile(r"^(me|project:[A-Za-z0-9][A-Za-z0-9._-]*)$")
RECORD_TYPES = {"case", "decision", "context"}
RECORD_DIRS = {"cases": "case", "decisions": "decision", "context": "context"}
TABLE_HEAD = ["사례", "한 줄 요약", "관련 규칙", "규칙과 관계"]
RELATIONS = {"규칙을 뒷받침", "규칙과 반대", "규칙 없음", "기각"}

def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]

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
    summarize = {}   # 요약에 나와야 하는 유효한 결정·맥락 id → 파일 이름
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
        # 사례·결정·맥락만 scope와 요약을 본다. raw/archive/ 아래 예전 기록은 건너뛴다.
        rel = p.relative_to(kb).parts
        kind = fm.get("type") or (RECORD_DIRS.get(rel[1]) if len(rel) > 2 else None)
        if kind in RECORD_TYPES and "archive" not in rel[:2]:
            scope = fm.get("scope")
            if not scope:
                problems.append(f"머리말 scope 없음: {p.relative_to(kb)}")
            elif not SCOPE_RE.match(scope):
                problems.append(f"scope 값이 me나 project:<이름>이 아님({scope}): {p.relative_to(kb)}")
            if (kind in ("decision", "context") and fm.get("status") == "active" and i
                    and fm.get("snapshot", "").lower() != "true"):
                summarize[i] = p.name
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
    summary = kb / "wiki" / "context.md"
    if summary.is_file():
        shown = set(ID_RE.findall(summary.read_text(encoding="utf-8")))
        for card in (kb / "wiki" / "projects").glob("*.md"):
            shown |= set(ID_RE.findall(card.read_text(encoding="utf-8")))
        for i in sorted(set(summarize) - shown):
            problems.append(f"요약(wiki/context.md, wiki/projects/)에 없는 유효한 기록: {i}")
    table = kb / "wiki" / "rule-cases.md"
    rows = 0
    if table.is_file():
        listed = set()
        head = None   # 표 머리 줄. 없으면 None
        for line in table.read_text(encoding="utf-8").splitlines():
            if not line.lstrip().startswith("|"): continue
            c = cells(line)
            if c[:1] == ["사례"]:
                head = head or c
                continue
            m = re.match(r"(C-\d{8}-\d{2})$", c[0])
            if m:
                listed.add(m.group(1)); rows += 1
                if len(c) < 4 or c[3] not in RELATIONS:
                    problems.append(f"규칙별 사례표 규칙과 관계 값이 넷 중 하나가 아님: {m.group(1)}")
        if head != TABLE_HEAD:
            problems.append("규칙별 사례표 표 머리가 | " + " | ".join(TABLE_HEAD) + " | 이 아님"
                            + (f"(지금: | {' | '.join(head)} |)" if head else "(표 머리 없음)"))
        for c in sorted(case_ids - listed):
            problems.append(f"규칙별 사례표에 없는 사례: {c}")
    print(f"점검 대상: {kb} · 원본 {len(raw_files)}개, 규칙별 사례표 "
          + (f"{rows}줄" if table.is_file() else "없음"))
    for x in problems: print("  [문제]", x)
    print("  통과" if not problems else f"  문제 {len(problems)}건")
    sys.exit(0 if not problems else 1)

if __name__ == "__main__":
    main()
