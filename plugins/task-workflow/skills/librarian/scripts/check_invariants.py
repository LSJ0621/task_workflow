#!/usr/bin/env python3
"""지식 베이스의 불변 조건을 점검한다. 사용: check_invariants.py <지식 베이스> [--skip-rule-cases] [--skip-summary]
종료 코드 0 = 통과. 점검: 식별자 중복 없음, 모든 원본에 id·date·status 머리말, 결정에 이유 절,
본문의 모든 C-·D-·X-·R- id 참조가 존재, superseded 쌍 일관,
사례·결정·맥락에 scope(me 또는 project:<이름>) 있음(raw/archive/ 아래는 예전 기록이라 건너뜀),
wiki/context.md가 있으면 유효한 결정·맥락 id가 wiki/context.md나 wiki/projects/*.md 어딘가에 있음
(머리말 snapshot: true 인 맥락은 그날의 상태라 건너뜀),
규칙별 사례표(wiki/rule-cases.md)가 있으면 표 머리가 지금 형식이고 모든 사례가 표에 있음.
status: draft 인 기록은 확인 전이라 "요약에 나와야 한다"와 "사례표에 있어야 한다" 검사에서 뺀다. 거꾸로 요약에 올라가 있으면 문제로 본다.
status: draft 인 결정은 "결정에 이유 절" 검사에서도 뺀다. 뽑지 못한 기록은 요지가 "아직 없음"이라서다. active 가 되면 본다.
이유 절은 예전 형식 "## 이유"와 새 틀의 "### 이유"("## 요지" 아래)를 둘 다 알아본다.
머리말에 source 가 있으면 session 이나 memo 여야 한다. source: session 이면 session·range 가 "-"가 아니고
본문에 <!-- extract:start --> 와 <!-- extract:end --> 가 하나씩 순서대로 있어야 한다.
source 가 없는 예전 기록은 이 검사를 하지 않는다. omitted, memo 칸은 있어도 되고 없어도 된다.
--skip-rule-cases 를 주면 "모든 사례가 표에 있음" 검사만 건너뛴다. 사례를 분류하기 전에 도는 점검(새벽 1단계 기록, 구조 점검, 사용자 분석)이 쓴다.
새 사례는 자가 발전(analyze-context)이 분류하기 전이라 표에 없는 게 맞아서다. 표 머리와 줄 형식은 그대로 본다.
--skip-summary 를 주면 "유효한 결정·맥락이 요약이나 카드에 나온다" 검사만 건너뛴다. 정리(4단계)보다 먼저 도는 점검(새벽 1단계 기록, 3단계 분석)이 쓴다.
새로 확정된 결정·맥락은 정리가 올리기 전이라 요약에 없는 게 맞아서다. draft 기록이 요약에 올라가 있는지는 그대로 본다.
두 옵션은 함께 줄 수 있다. 옵션 없이 돌리면 전부 본다. 정리(4단계)가 그렇게 돌린다.
raw/reviews/ 의 점검 보고서(HTML)는 머리말과 식별자가 없는 파일이라 머리말 점검에서 뺀다(raw/archive/reviews/ 는 예전 기록이라 그대로 본다).
raw/reports/ 의 아침 보고서도 머리말과 식별자가 없는 파일이라 머리말 점검에서 뺀다(raw/archive/reports/ 는 예전 기록이라 그대로 본다).
아침 보고서와 추정 기록(wiki/hypotheses.md)에 적힌 C-·D-·X- id 참조는 다른 문서처럼 존재하는지 본다. H- 번호는 기록 id가 아니라 보지 않는다.
P-로 시작하는 옛 기준 항목 id는 없어진 기준 문서의 이름이라 지난 기록에 남아 있어도 점검하지 않는다."""
import pathlib, re, sys

ID_RE = re.compile(r"\b([CDXR]-\d{8}-\d{2})\b")
SCOPE_RE = re.compile(r"^(me|project:[A-Za-z0-9][A-Za-z0-9._-]*)$")
RECORD_TYPES = {"case", "decision", "context"}
RECORD_DIRS = {"cases": "case", "decisions": "decision", "context": "context"}
TABLE_HEAD = ["사례", "한 줄 요약", "관련 규칙", "규칙과 관계"]
RELATIONS = {"규칙을 뒷받침", "규칙과 반대", "규칙 없음", "기각"}

USAGE = "사용: check_invariants.py <지식 베이스> [--skip-rule-cases] [--skip-summary]"
NO_FRONTMATTER_DIRS = {"journal", "reviews", "reports"}   # raw/ 바로 아래에서 머리말 없이 쌓는 폴더
SOURCES = {"session", "memo"}
EXTRACT_START = "<!-- extract:start -->"
EXTRACT_END = "<!-- extract:end -->"
REASON_RE = re.compile(r"^#{2,3} 이유", re.M)   # 예전 형식 "## 이유"와 새 틀의 "## 요지" 아래 "### 이유"

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

def check_source(fm, text, name):
    """머리말 source 칸과 그에 딸린 session·range·표시를 본다. source 가 없으면 예전 기록이라 보지 않는다."""
    source = fm.get("source")
    if not source:
        return []
    if source not in SOURCES:
        return [f"source 값이 session이나 memo가 아님({source}): {name}"]
    if source != "session":
        return []
    found = []
    for k in ("session", "range"):
        if fm.get(k, "").strip("\"'") in ("", "-"):
            found.append(f"source: session 인데 {k} 없음: {name}")
    body = re.sub(r"^---\n.*?\n---", "", text, count=1, flags=re.S)
    starts, ends = body.count(EXTRACT_START), body.count(EXTRACT_END)
    if starts != 1 or ends != 1:
        found.append(f"source: session 인데 extract 표시가 하나씩이 아님(start {starts}개, end {ends}개): {name}")
    elif body.index(EXTRACT_START) > body.index(EXTRACT_END):
        found.append(f"extract 표시 순서가 뒤바뀜: {name}")
    return found

def main():
    options = [a for a in sys.argv[1:] if a.startswith("--")]
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(paths) != 1 or set(options) - {"--skip-rule-cases", "--skip-summary"}:
        sys.exit(USAGE)
    skip_rule_cases = "--skip-rule-cases" in options
    skip_summary = "--skip-summary" in options
    kb = pathlib.Path(paths[0]).expanduser()
    problems = []
    ids = {}
    case_ids = set()
    draft_ids = {}   # 확인 전(status: draft) 기록 id → 파일 이름. 요약에 올라가 있으면 안 된다
    summarize = {}   # 요약에 나와야 하는 유효한 결정·맥락 id → 파일 이름
    # 메모(raw/journal/), 점검 보고서(raw/reviews/), 아침 보고서(raw/reports/)는 머리말이 없는 파일이다.
    raw_files = [p for p in kb.glob("raw/**/*.md")
                 if p.relative_to(kb).parts[1] not in NO_FRONTMATTER_DIRS]
    reports = [p for p in (kb / "raw" / "reviews").glob("*.html")]
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
            # 확인 전 사례는 자가 발전이 읽지 않으므로 사례표에 없어도 된다.
            if fm.get("type") == "case" and fm.get("status") != "draft": case_ids.add(i)
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
            if fm.get("status") == "draft" and i:
                draft_ids[i] = p.name
            problems += check_source(fm, text, p.name)
        # 확인 전(draft) 결정은 뽑지 못해 요지가 비어 있을 수 있어 이유 절을 보지 않는다. active가 되면 본다.
        if fm.get("type") == "decision" and fm.get("status") != "draft" and not REASON_RE.search(text):
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
        for i in sorted(set(summarize) - shown) if not skip_summary else []:
            problems.append(f"요약(wiki/context.md, wiki/projects/)에 없는 유효한 기록: {i}")
        for i in sorted(set(draft_ids) & shown):
            problems.append(f"확인 전(draft) 기록이 요약(wiki/context.md, wiki/projects/)에 올라가 있음: {i}")
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
        if not skip_rule_cases:
            for c in sorted(case_ids - listed):
                problems.append(f"규칙별 사례표에 없는 사례: {c}")
    print(f"점검 대상: {kb} · 원본 {len(raw_files)}개, 점검 보고서 {len(reports)}개, 규칙별 사례표 "
          + (f"{rows}줄" if table.is_file() else "없음")
          + (" (표에 없는 사례 검사는 건너뜀)" if skip_rule_cases else "")
          + (" (요약에 없는 기록 검사는 건너뜀)" if skip_summary else ""))
    for x in problems: print("  [문제]", x)
    print("  통과" if not problems else f"  문제 {len(problems)}건")
    sys.exit(0 if not problems else 1)

if __name__ == "__main__":
    main()
