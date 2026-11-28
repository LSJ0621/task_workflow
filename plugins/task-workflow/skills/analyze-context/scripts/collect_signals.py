#!/usr/bin/env python3
"""대화 기록(세션 기록)에서 하루치 사용자 입력을 뽑고, 가른 결과를 받아 지식 베이스에 날짜별 목록으로 쌓는다.
새벽 작업의 모으기 단계가 쓴다. 무엇이 지적이고 되물음인지는 낱말로 가를 수 없어서, 이 스크립트는 후보를 뽑고
목록을 쓰는 일만 하고 가르는 일은 서브에이전트가 한다.

명령
  candidates [<지식 베이스>] [--day YYYY-MM-DD ...] [--today YYYY-MM-DD] [--out <폴더>] [--projects-dir <폴더>]
      날마다 후보 파일 <out>/<날짜>.candidates.md 를 쓴다. 날을 안 주면 아직 목록이 없는 날이다:
      가장 새 목록의 다음 날부터 어제까지, 많아도 7일. 목록이 하나도 없으면 어제 하루다.
      날마다 "<날짜> | 후보 n건 | <후보 파일>" 한 줄을 찍고 마지막 줄에 "합계 n일"을 찍는다.
  write [<지식 베이스>] --day YYYY-MM-DD --decisions <파일> [--list-dir <폴더>] [--projects-dir <폴더>]
      그날의 후보를 다시 뽑아, 가른 결과 파일에 적힌 후보만 목록 <지식 베이스>/evolve/signals/<날짜>.md 로 쓴다.
      --list-dir 을 주면 목록을 그 폴더에 쓴다(시험할 때). 같은 날의 목록이 있으면 덮어쓴다.
종료 코드 0 성공, 1 환경이나 가른 결과 파일의 오류, 2 인자 오류.

후보는 그날(이 컴퓨터의 시간대) 사람이 친 입력 전부다. 예약 작업 세션과 서브에이전트 기록은 빼고, 이어 연 세션에
복사된 같은 줄은 한 번만 싣는다. 읽는 방법은 세는 스크립트(count_recurrence.py)와 같다.
후보마다 앞 답의 머리와 끝, 사용자 글, 같은 세션의 메모 줄, 이미 있는 메모나 기록을 적는다.
이미 있는지는 두 가지로 본다. 그 입력이 어느 기록(raw/cases, raw/decisions, raw/context)의 세션과 범위 안에 있다.
또는 같은 세션의 메모(raw/journal)가 `사용자 말:`의 따옴표 안에 그 입력의 구절을 그대로 옮겼다.

가른 결과 파일은 한 줄에 후보 하나다. 목록에 실을 후보만 적는다.
  <후보 id> | <지적|다시 물음|만족|선택> [| <없음|메모 HH:MM|기록 id>] [| 가림]
  셋째 칸을 비우거나 `-`로 두면 스크립트가 찾은 값을 쓴다. `가림`을 붙이면 사용자 말을 싣지 않는다.
  빈 줄과 `#`로 시작하는 줄은 넘어간다.

목록의 사용자 말은 한 줄로 줄인 첫 80자다. 비밀값 모양이 보이면 말을 통째로 가리고,
클라우드 자원 id, 12자리 계정 번호, IP 주소, 클라우드 호스트 이름 모양은 그 자리만 가린다.

세션 기록은 --projects-dir, 없으면 <Claude 설정 폴더>/projects 에서 읽는다.
"""
import argparse, datetime, json, os, pathlib, re, sys

KINDS = ("지적", "다시 물음", "만족", "선택")
SHOW = 80
HEAD, TAIL, USER_SHOW = 150, 300, 600
MAX_DAYS = 7
LIST_DIR = ("evolve", "signals")
RECORD_DIRS = ("cases", "decisions", "context")
SECRET_MASK = "[비밀값이 있어 가림]"
HIDDEN = "[가림]"
REPLY_MARK = "<!-- reply"
MEMO_RE = re.compile(r"^(\d{1,2}:\d{2}) \| ")
QUOTE_RE = re.compile(r"[\"“]([^\"“”]{6,})[\"”]")
HAVE_RE = re.compile(r"^(없음|메모 \d{1,2}:\d{2}|[CDX]-\d{8}-\d{2})$")
INFRA_PATTERNS = (
    re.compile(r"arn:aws[\w-]*:[\w:/.*-]+"),
    re.compile(r"\b(?:vpc|subnet|sg|igw|rtb|eni|nat|acl|vol|snap|ami|i|eipalloc|tgw|pcx|vpce)-[0-9a-f]{8,17}\b"),
    re.compile(r"(?<![\d.])\d{12}(?![\d.])"),
    re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"),
    re.compile(r"[\w.-]+\.(?:amazonaws\.com|azure\.com|windows\.net|googleapis\.com|cloudapp\.net)\b"),
)
INTRO = "새벽 작업의 모으기 단계가 대화 기록에서 모은 것이다. `collect_signals.py`(자가 발전 스킬의 스크립트)가 쓴다. 손으로 고치지 않는다."
HEADER = ["시각", "세션", "종류", "사용자 말", "메모·기록"]


def fail(message):
    sys.stderr.write(message + "\n")
    sys.exit(1)


def load_counter():
    """세는 스크립트. 세션 기록을 턴으로 읽는 방법을 한 곳에서만 정하려고 빌려 쓴다."""
    import importlib.util
    path = pathlib.Path(__file__).resolve().parent / "count_recurrence.py"
    if not path.is_file():
        fail(f"스크립트를 못 찾음: {path}")
    spec = importlib.util.spec_from_file_location("count_recurrence", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one_line(text):
    return " ".join(text.split())


def hide_infra(text):
    for pattern in INFRA_PATTERNS:
        text = pattern.sub(HIDDEN, text)
    return text


def safe(text, limit, find_secret):
    """한 줄로 줄이고 가릴 것을 가린 글. 표의 칸을 깨는 `|`는 `/`로 바꾼다."""
    if find_secret(text):
        return SECRET_MASK
    return hide_infra(one_line(text))[:limit].replace("|", "/")

# ---------------------------------------------------------------------------
# 지식 베이스: 메모와 기록
# ---------------------------------------------------------------------------

def read_memos(kb, day):
    """그날과 다음 날 메모 파일의 메모 줄. [{time, kind, title, session, quotes, next_day}]"""
    memos = []
    for offset in (0, 1):
        path = kb / "raw" / "journal" / f"{(day + datetime.timedelta(days=offset)).isoformat()}.md"
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not MEMO_RE.match(line):
                continue
            cells = [cell.strip() for cell in line.split(" | ")]
            session = next((cell[len("session:"):] for cell in cells[5:] if cell.startswith("session:")), "-")
            body = cells[3] if len(cells) > 3 else ""
            said = body.split("사용자 말:", 1)[1] if "사용자 말:" in body else ""
            said = re.split(r"풀이:|바꾸는 것:", said)[0]
            memos.append({"time": cells[0].zfill(5), "kind": cells[1] if len(cells) > 1 else "",
                          "title": cells[2] if len(cells) > 2 else "", "session": session,
                          "quotes": [one_line(quote) for quote in QUOTE_RE.findall(said)], "next_day": bool(offset)})
    return memos


def front_matter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    fields = {}
    for line in m.group(1).splitlines() if m else []:
        if ":" in line:
            name, value = line.split(":", 1)
            fields[name.strip()] = value.strip()
    return fields


def read_records(kb, day):
    """그날 앞뒤 하루에 난 기록 가운데 세션과 범위가 적힌 것. [{id, session, first, last}]"""
    near = {(day + datetime.timedelta(days=offset)).isoformat() for offset in (-1, 0, 1)}
    records = []
    for folder in RECORD_DIRS:
        for path in sorted((kb / "raw" / folder).glob("*.md")):
            fields = front_matter(path.read_text(encoding="utf-8"))
            first, sep, last = fields.get("range", "").partition("..")
            if fields.get("date") in near and sep and fields.get("id") and fields.get("session", "-") != "-":
                records.append({"id": fields["id"], "session": fields["session"], "first": first.strip(), "last": last.strip()})
    return records


def line_order(path):
    """세션 기록 파일의 {uuid: 줄 순서}"""
    order = {}
    try:
        handle = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return order
    with handle:
        for number, line in enumerate(handle):
            m = re.search(r'"uuid"\s*:\s*"([^"]+)"', line)
            if m:
                try:
                    uuid = json.loads(line).get("uuid")
                except (ValueError, AttributeError):
                    uuid = None
                if isinstance(uuid, str):
                    order.setdefault(uuid, number)
    return order


class Covered:
    """입력 하나가 이미 메모나 기록에 있는지 본다."""

    def __init__(self, kb, day, paths):
        self.memos, self.records = read_memos(kb, day), read_records(kb, day)
        self.paths, self.orders = paths, {}

    def order(self, session):
        if session not in self.orders:
            self.orders[session] = line_order(self.paths[session]) if session in self.paths else {}
        return self.orders[session]

    def record(self, uuid):
        for record in self.records:
            order = self.order(record["session"])
            if uuid in order and record["first"] in order and record["last"] in order \
                    and order[record["first"]] <= order[uuid] <= order[record["last"]]:
                return record["id"]
        return None

    def memos_of(self, session):
        return [memo for memo in self.memos if memo["session"] == session]

    def memo(self, session, text):
        line = one_line(text)
        for memo in self.memos:
            if memo["session"] in (session, "-") and any(quote in line for quote in memo["quotes"]):
                return "메모 " + memo["time"]
        return None

    def found(self, session, uuid, text):
        return self.record(uuid) or self.memo(session, text) or "없음"

# ---------------------------------------------------------------------------
# 후보
# ---------------------------------------------------------------------------

def collect(kb, day, projects, counter):
    """그날의 후보. [{id, uuid, session, stamp, text, before, memos, have, quoted}] 시각 순."""
    measure = counter.load_measure()
    extractor = measure.load_extractor()
    start = datetime.datetime.combine(day, datetime.time()).astimezone()
    end = start + datetime.timedelta(days=1)
    sessions, _ = counter.read_sessions(projects, extractor, measure, floor=start)
    paths = {path.name[:-len(".jsonl")]: path for path in counter.session_paths(projects)}
    covered, seen, rows = Covered(kb, day, paths), set(), []
    for sid, turns in sessions:
        for index, turn in enumerate(turns):
            if not turn["user"] or not isinstance(turn["key"], str) or turn["key"] in seen:
                continue
            stamp, text = turn["user"][0]
            when = counter.moment_of(stamp)
            if when is None or not (start <= when < end) or not text.strip():
                continue
            seen.add(turn["key"])
            before = turns[index - 1]["agent"][-1][1] if index and turns[index - 1]["agent"] else ""
            rows.append({"uuid": turn["key"], "session": sid, "when": when, "text": text, "before": before,
                         "memos": covered.memos_of(sid), "have": covered.found(sid, turn["key"], text),
                         "quoted": REPLY_MARK in text})
    rows.sort(key=lambda row: (row["when"], row["session"], row["uuid"]))
    width = 8
    while len({row["uuid"][:width] for row in rows}) < len(rows) and width < 36:
        width += 4
    for row in rows:
        row["id"] = row["uuid"][:width]
    return rows, extractor.find_secret


def candidate_text(day, rows, find_secret):
    lines = [f"# 모으기 후보 {day.isoformat()}", "",
             f"그날 사람이 친 입력 {len(rows)}건이다. 이 파일은 임시 파일이고 지식 베이스에 넣지 않는다.", ""]
    for row in rows:
        before = one_line(row["before"])
        if len(before) > HEAD + TAIL:
            before = before[:HEAD] + " … " + before[-TAIL:]
        marks = " | 인용 답장" if row["quoted"] else ""
        lines.append(f"## {row['id']} | {row['when'].strftime('%H:%M')} | 세션 {row['session']}{marks}")
        lines.append("- 앞 답: " + (safe(before, HEAD + TAIL + 3, find_secret) if before else "없음"))
        lines.append("- 사용자: " + safe(row["text"], USER_SHOW, find_secret))
        memos = [f"{'다음 날 ' if memo['next_day'] else ''}{memo['time']} {memo['kind']} {safe(memo['title'], 40, find_secret)}"
                 for memo in row["memos"]]
        lines.append("- 같은 세션의 메모: " + ("; ".join(memos) if memos else "없음"))
        lines.append("- 이미 있는 메모·기록: " + row["have"])
        lines.append("")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# 목록
# ---------------------------------------------------------------------------

def read_decisions(path, rows):
    by_id = {row["id"]: row for row in rows}
    picked = {}
    for number, raw in enumerate(pathlib.Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cells = [cell.strip() for cell in line.split("|")]
        hide = cells[-1] == "가림"
        cells = cells[:-1] if hide else cells
        if len(cells) not in (2, 3) or cells[0] not in by_id or cells[1] not in KINDS:
            fail(f"가른 결과 {number}번째 줄을 읽을 수 없다(후보 id | {'|'.join(KINDS)} [| 없음|메모 HH:MM|기록 id] [| 가림]): {raw}")
        have = cells[2] if len(cells) == 3 and cells[2] not in ("", "-") else by_id[cells[0]]["have"]
        if not HAVE_RE.match(have):
            fail(f"가른 결과 {number}번째 줄의 셋째 칸은 없음, 메모 HH:MM, 기록 id 가운데 하나다: {raw}")
        if cells[0] in picked:
            fail(f"가른 결과에 같은 후보가 두 번 있다: {cells[0]}")
        picked[cells[0]] = (cells[1], have, hide)
    return picked


def list_text(day, rows, picked, find_secret):
    kept = [row for row in rows if row["id"] in picked]
    counts = {kind: sum(1 for row in kept if picked[row["id"]][0] == kind) for kind in KINDS}
    bare = sum(1 for row in kept if picked[row["id"]][0] == "지적" and picked[row["id"]][1] == "없음")
    summary = (f"사용자 입력 {len(rows)}건 가운데 {len(kept)}줄. 지적 {counts['지적']}(메모·기록 없음 {bare}), "
               f"다시 물음 {counts['다시 물음']}, 만족 {counts['만족']}, 선택 {counts['선택']}.")
    lines = [f"# 모은 말 {day.isoformat()}", "", INTRO, summary, "",
             "| " + " | ".join(HEADER) + " |", "| :- | :- | :- | :- | :- |"]
    for row in kept:
        kind, have, hide = picked[row["id"]]
        said = HIDDEN if hide else safe(row["text"], SHOW, find_secret)
        lines.append("| " + " | ".join([row["when"].strftime("%H:%M"), row["session"], kind, said, have]) + " |")
    return "\n".join(lines) + "\n", summary


# ---------------------------------------------------------------------------

def parse_day(value):
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        fail(f"날짜는 YYYY-MM-DD로 적는다: {value}")


def knowledge_base(a):
    if not a.knowledge_base:
        fail("지식 베이스를 모른다. 인자로 주거나 KNOWLEDGE_BASE_DIR 을 둔다")
    kb = pathlib.Path(a.knowledge_base).expanduser()
    if not (kb / "raw" / "journal").is_dir():
        fail(f"지식 베이스가 아님(raw/journal 없음): {kb}")
    return kb


def projects_dir(a, counter):
    return pathlib.Path(a.projects_dir).expanduser() if a.projects_dir else counter.load_measure().claude_dir() / "projects"


def days_to_collect(kb, today):
    yesterday = today - datetime.timedelta(days=1)
    done = []
    for path in kb.joinpath(*LIST_DIR).glob("*.md"):
        try:
            done.append(datetime.date.fromisoformat(path.stem))
        except ValueError:
            continue
    first = max(done) + datetime.timedelta(days=1) if done else yesterday
    first = max(first, yesterday - datetime.timedelta(days=MAX_DAYS - 1))
    return [first + datetime.timedelta(days=step) for step in range((yesterday - first).days + 1)]


def cmd_candidates(a):
    kb, counter = knowledge_base(a), load_counter()
    today = parse_day(a.today) if a.today else datetime.date.today()
    days = [parse_day(value) for value in a.day] if a.day else days_to_collect(kb, today)
    out = pathlib.Path(a.out).expanduser() if a.out else pathlib.Path("/tmp") / f"collect-signals-{today.isoformat()}"
    out.mkdir(parents=True, exist_ok=True)
    for day in days:
        rows, find_secret = collect(kb, day, projects_dir(a, counter), counter)
        target = out / f"{day.isoformat()}.candidates.md"
        target.write_text(candidate_text(day, rows, find_secret), encoding="utf-8")
        print(f"{day.isoformat()} | 후보 {len(rows)}건 | {target}")
    print(f"합계 {len(days)}일")


def cmd_write(a):
    kb, counter = knowledge_base(a), load_counter()
    day = parse_day(a.day)
    if not pathlib.Path(a.decisions).is_file():
        fail(f"가른 결과 파일이 없다: {a.decisions}")
    rows, find_secret = collect(kb, day, projects_dir(a, counter), counter)
    text, summary = list_text(day, rows, read_decisions(a.decisions, rows), find_secret)
    folder = pathlib.Path(a.list_dir).expanduser() if a.list_dir else kb.joinpath(*LIST_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{day.isoformat()}.md"
    target.write_text(text, encoding="utf-8")
    print(f"씀: {target}")
    print(summary)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("candidates")
    c.add_argument("knowledge_base", nargs="?", default=os.environ.get("KNOWLEDGE_BASE_DIR"))
    c.add_argument("--day", action="append", default=[])
    c.add_argument("--today")
    c.add_argument("--out")
    c.add_argument("--projects-dir")
    c.set_defaults(run=cmd_candidates)
    w = sub.add_parser("write")
    w.add_argument("knowledge_base", nargs="?", default=os.environ.get("KNOWLEDGE_BASE_DIR"))
    w.add_argument("--day", required=True)
    w.add_argument("--decisions", required=True)
    w.add_argument("--list-dir")
    w.add_argument("--projects-dir")
    w.set_defaults(run=cmd_write)
    a = ap.parse_args()
    a.run(a)


if __name__ == "__main__":
    main()
