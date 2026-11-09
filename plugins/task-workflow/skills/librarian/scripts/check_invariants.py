#!/usr/bin/env python3
"""지식 베이스의 불변 조건을 점검한다. 사용: check_invariants.py <지식 베이스>
종료 코드 0 = 통과. 점검: 식별자 중복 없음, 모든 원본에 id·date·status 머리말, 결정에 이유 절,
기준 항목마다 출처가 실제 원본을 가리킴, 본문의 모든 id 참조가 존재, superseded 쌍 일관."""
import pathlib, re, sys

def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1); fm[k.strip()] = v.split("#")[0].strip()
    return fm

def main():
    kb = pathlib.Path(sys.argv[1]).expanduser()
    problems = []
    ids = {}
    raw_files = [p for p in kb.glob("raw/**/*.md") if "journal" not in p.parts]
    for p in raw_files:
        fm = frontmatter(p.read_text(encoding="utf-8"))
        for k in ("id", "date", "status"):
            if not fm.get(k):
                problems.append(f"머리말 {k} 없음: {p.relative_to(kb)}")
        i = fm.get("id")
        if i:
            if i in ids: problems.append(f"식별자 중복: {i} ({p.name}, {ids[i]})")
            ids[i] = p.name
            if not p.name.startswith(i): problems.append(f"파일명이 id로 시작하지 않음: {p.name}")
        if fm.get("type") == "decision" and "## 이유" not in p.read_text(encoding="utf-8"):
            problems.append(f"결정에 이유 절 없음: {p.name}")
        if fm.get("status") == "superseded" and not fm.get("superseded_by"):
            problems.append(f"superseded 인데 superseded_by 없음: {p.name}")
    crit_ids = set()
    for p in kb.glob("wiki/criteria/*.md"):
        text = p.read_text(encoding="utf-8")
        for sec in re.split(r"^## ", text, flags=re.M)[1:]:
            head = sec.splitlines()[0]
            m = re.match(r"(P-[A-Z]+-\d+)", head)
            if not m: continue
            crit_ids.add(m.group(1))
            src = re.search(r"- 출처: (.*)", sec)
            if not src or not re.search(r"[CDXR]-\d{8}-\d{2}", src.group(1)):
                problems.append(f"기준 {m.group(1)} 에 원본 출처 없음 ({p.name})")
    all_ids = set(ids) | crit_ids
    # 메모는 정식 기록 전 재료라 id 참조 점검에서 뺀다. 숨김 폴더(.git, .claude 등)도 뺀다.
    skip = {"journal"}
    for p in kb.glob("**/*.md"):
        rel = p.relative_to(kb).parts
        if any(x.startswith(".") for x in rel) or skip & set(rel): continue
        body = p.read_text(encoding="utf-8")
        for ref in set(re.findall(r"\b([CDXR]-\d{8}-\d{2}|P-[A-Z]+-\d{2,})\b", body)):
            if ref not in all_ids and "{{" not in ref:
                problems.append(f"없는 id 참조 {ref}: {p.relative_to(kb)}")
    print(f"점검 대상: {kb} · 원본 {len(raw_files)}개, 기준 {len(crit_ids)}개")
    for x in problems: print("  [문제]", x)
    print("  통과" if not problems else f"  문제 {len(problems)}건")
    sys.exit(0 if not problems else 1)

if __name__ == "__main__":
    main()
