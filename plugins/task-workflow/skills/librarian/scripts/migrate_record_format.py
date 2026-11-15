#!/usr/bin/env python3
"""예전 기록(사례·결정·맥락)을 새 형식으로 옮긴다. 사용: migrate_record_format.py <지식 베이스> [--dry-run]

문장은 한 글자도 바꾸지 않는다. 절 이름과 순서, 머리말 칸만 바꾼다.
- 사례(raw/cases/): `## 어떤 작업에서`·`## 에이전트가 한 것`·`## 사용자가 고친 말`은 `## 있었던 일` 아래 `###`로,
  `## 에이전트 풀이`·`## 왜 문제인가`는 `## 분석` 아래 `###`로 옮긴다. 이름을 모르는 절은 버리지 않고
  원래 위치에 따라 나눈다. `에이전트 풀이`나 `왜 문제인가`보다 앞에 있던 절은 `## 있었던 일` 아래에,
  그 뒤에 있던 절은 `## 분석` 아래에 `###`로 둔다. 둘 다 없는 사례는 모르는 절을 전부 `## 있었던 일` 아래에 두고
  `## 분석`은 제목만 둔다. 더하는 것은 제목 줄뿐이다. 머리말에 source: memo, session: -, range: - 를 더한다.
- 결정(raw/decisions/)·맥락(raw/context/): 본문은 그대로 두고 머리말에 source: memo 만 더한다.
- 머리말에 source 가 이미 있는 파일은 새 형식이라 건너뛴다. raw/archive/ 는 보지 않는다.

옮기기 전후를 비교한다. 본문 줄(`#`로 시작하는 제목 줄과 빈 줄을 뺀 나머지)이 처음부터 끝까지 순서 그대로 같아야 한다.
다르면 그 파일을 고치지 않고 이름을 보고한다. --dry-run 은 아무 파일도 고치지 않고 건수만 낸다.
종료 코드 0 = 비교에서 걸린 파일 없음. 1 = 걸린 파일 있음 또는 사용법 오류."""
import pathlib, re, sys

USAGE = "사용: migrate_record_format.py <지식 베이스> [--dry-run]"
HAPPENED = "있었던 일"
ANALYSIS = "분석"
TO_HAPPENED = ["어떤 작업에서", "에이전트가 한 것", "사용자가 고친 말"]
TO_ANALYSIS = ["에이전트 풀이", "왜 문제인가"]
FENCE_RE = re.compile(r"^\s*(```|~~~)")
H2_RE = re.compile(r"^## +(.+?)\s*$")
HEADING_RE = re.compile(r"^(#+)( .*)$")

def split_frontmatter(text):
    """(머리말 줄들, 본문 글)을 돌려준다. 머리말이 없으면 (None, text)."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text
    return m.group(1).split("\n"), text[m.end():]

def has_key(fm_lines, key):
    return any(re.match(rf"^{key}\s*:", line) for line in fm_lines)

def add_keys(fm_lines, pairs):
    """status 줄 바로 아래에 새 칸을 넣는다. status 줄이 없으면 머리말 끝에 넣는다."""
    new = [f"{k}: {v}" for k, v in pairs]
    for n, line in enumerate(fm_lines):
        if re.match(r"^status\s*:", line):
            return fm_lines[:n + 1] + new + fm_lines[n + 1:]
    return fm_lines + new

def content_lines(lines):
    """비교에 쓰는 본문 줄. 제목 줄(#로 시작)과 빈 줄을 뺀다."""
    return [l for l in lines if l.strip() and not l.startswith("#")]

def split_sections(body, level_re=H2_RE):
    """본문을 (앞부분 줄들, [(절 이름, 그 절의 줄들)])로 나눈다. 코드 블록 안의 ## 는 제목으로 보지 않는다."""
    head, sections, fenced = [], [], False
    for line in body.split("\n"):
        if FENCE_RE.match(line):
            fenced = not fenced
        m = None if fenced else level_re.match(line)
        if m:
            sections.append((m.group(1), []))
        elif sections:
            sections[-1][1].append(line)
        else:
            head.append(line)
    return head, sections

def demote(lines):
    """절 안의 작은 제목을 한 단계 내린다(### → ####). 절이 한 단계 내려가서다."""
    out, fenced = [], False
    for line in lines:
        if FENCE_RE.match(line):
            fenced = not fenced
        m = None if fenced else HEADING_RE.match(line)
        out.append("#" + line if m else line)
    return out

def trim(lines):
    """앞뒤 빈 줄을 뗀다."""
    a, b = 0, len(lines)
    while a < b and not lines[a].strip(): a += 1
    while b > a and not lines[b - 1].strip(): b -= 1
    return lines[a:b]

def migrate_case_body(body):
    """사례 본문을 새 절로 옮긴 글을 돌려준다. 옮길 수 없으면 (None, 이유)."""
    head, sections = split_sections(body)
    names = [n for n, _ in sections]
    if HAPPENED in names or ANALYSIS in names:
        return None, "이미 `## 있었던 일`이나 `## 분석` 절이 있다"
    if len(set(names)) != len(names):
        return None, "같은 이름의 절이 두 번 나온다"
    # 분석 절(에이전트 풀이, 왜 문제인가)이 처음 나오는 곳에서 가른다. 앞은 있었던 일, 거기부터는 분석이다.
    cut = next((n for n, name in enumerate(names) if name in TO_ANALYSIS), len(sections))
    happened, analysis = sections[:cut], sections[cut:]
    late = [n for n, _ in analysis if n in TO_HAPPENED]
    if late:
        return None, "있었던 일에 갈 절이 분석 절 뒤에 있다: " + ", ".join(late)
    while head and not head[-1].strip():   # 제목 위의 빈 줄은 그대로 두고 끝의 빈 줄만 뗀다
        head = head[:-1]
    out = head + [""]
    for title, group in ((HAPPENED, happened), (ANALYSIS, analysis)):
        out += [f"## {title}", ""]
        for name, lines in group:
            out += [f"### {name}"] + trim(demote(lines)) + [""]
    return "\n".join(out), ""

def same_sentences(old_body, new_body):
    """옮기기 전후의 본문 줄이 처음부터 끝까지 순서 그대로 같은지 본다. 다르면 이유를, 같으면 None 을 돌려준다."""
    old, new = content_lines(old_body.split("\n")), content_lines(new_body.split("\n"))
    if old == new:
        return None
    for n, (x, y) in enumerate(zip(old, new), 1):
        if x != y:
            return f"본문 줄이 다르다({n}번째 줄부터)"
    return f"본문 줄 수가 다르다(전 {len(old)}줄, 후 {len(new)}줄)"

def migrate(path, kind):
    """(새 글 또는 None, 상태, 이유). 상태는 migrated | skipped | failed."""
    text = path.read_text(encoding="utf-8")
    if "\r" in text:
        return None, "failed", "줄 끝이 CRLF다"
    fm, body = split_frontmatter(text)
    if fm is None:
        return None, "failed", "머리말이 없다"
    if has_key(fm, "source"):
        return None, "skipped", ""
    if kind == "case":
        for k in ("session", "range"):
            if has_key(fm, k):
                return None, "failed", f"source 없이 {k} 칸만 있다"
        new_body, why = migrate_case_body(body)
        if new_body is None:
            return None, "failed", why
        why = same_sentences(body, new_body)
        if why:
            return None, "failed", why
        fm = add_keys(fm, [("source", "memo"), ("session", "-"), ("range", "-")])
    else:
        new_body = body
        fm = add_keys(fm, [("source", "memo")])
    return "---\n" + "\n".join(fm) + "\n---\n" + new_body, "migrated", ""

def main():
    options = [a for a in sys.argv[1:] if a.startswith("--")]
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(paths) != 1 or set(options) - {"--dry-run"}:
        print(USAGE, file=sys.stderr); sys.exit(1)
    dry = "--dry-run" in options
    kb = pathlib.Path(paths[0]).expanduser()
    if not (kb / "raw").is_dir():
        print(f"raw/ 폴더가 없다: {kb}", file=sys.stderr); sys.exit(1)
    failed = []
    print(f"대상: {kb}" + (" (dry-run. 파일을 고치지 않는다)" if dry else ""))
    for folder, kind, label in (("cases", "case", "사례"), ("decisions", "decision", "결정"), ("context", "context", "맥락")):
        count = {"migrated": 0, "skipped": 0, "failed": 0}
        for p in sorted((kb / "raw" / folder).glob("*.md")):
            new, state, why = migrate(p, kind)
            count[state] += 1
            if state == "failed":
                failed.append((p.relative_to(kb), why))
            elif state == "migrated" and not dry:
                p.write_text(new, encoding="utf-8")
        print(f"  {label}: 옮김 {count['migrated']}건, 이미 새 형식이라 건너뜀 {count['skipped']}건, "
              f"비교에서 걸림 {count['failed']}건")
    for rel, why in failed:
        print(f"  [걸림] {rel}: {why}")
    print("  걸린 파일 없음" if not failed else f"  걸린 파일 {len(failed)}건. 이 파일들은 고치지 않았다")
    sys.exit(0 if not failed else 1)

if __name__ == "__main__":
    main()
