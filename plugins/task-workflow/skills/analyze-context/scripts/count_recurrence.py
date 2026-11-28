#!/usr/bin/env python3
"""대화 기록(세션 기록)에서 "같은 상황"이 온 횟수와 그 가운데 "재발"한 횟수를 센다.
추정 기록의 시도마다 적힌 "셀 것"을 볼 날짜에 세는 데 쓴다. 걸린 줄을 모두 찍으니 사람이 읽고 확인할 수 있다.

명령
  count --since <때> [--until <때>] --same <조건> [--same <조건> ...] [--recur <조건> ...]
        [--within <턴 수>] [--per turn|session] [--session <세션 id>] [--json] [--projects-dir <폴더>]
      같은 상황과 재발을 센다. 마지막 줄이 "같은 상황 n번 중 재발 m번"이다.
  due [<지식 베이스>] [--today YYYY-MM-DD]
      추정 기록(evolve/hypotheses.md)에서 상태가 "지켜보는 중"이고 볼 날짜가 오늘이거나 지난 시도를 찍는다.
      볼 날짜 줄이 없는 시도도 찍는다. 마지막 줄이 "합계 n"이다. 세션 기록은 읽지 않는다.
종료 코드 0 성공, 1 조건이나 환경 오류, 2 인자 오류.

세는 단위는 턴이다. 턴은 사용자 입력 하나와, 다음 사용자 입력 전까지 에이전트가 한 말과 부른 스킬이다.

조건은 `<어디>:<정규식>` 꼴이다. 어디는 넷 가운데 하나다.
  user   사용자가 친 글. 인용 답장 표시(`<!-- reply`)처럼 입력에 붙어 온 표시도 이 글에 있다
  agent  에이전트가 사용자에게 보인 글
  skill  그 턴에 부른 스킬 이름(Skill 도구로 부른 것과 사용자가 `/이름`으로 친 것)
  hook   그 입력에 훅(UserPromptSubmit)이 붙인 알림 글
  어디 앞에 `!`를 붙이면(`!hook:...`) 그 턴에 그런 것이 없을 때 맞는다.
정규식은 파이썬 re 문법이고 대소문자를 가린다. 낱말만 적어도 된다.

- --same 을 여러 번 주면 한 턴에서 모두 맞아야 같은 상황이다.
- --recur 는 재발 조건이다. 여러 번 주면 한 턴에서 모두 맞아야 재발이다. 안 주면 같은 상황만 센다.
- --within 0(기본)이면 재발 조건을 같은 상황과 같은 턴에서 본다(예: 그 입력에 훅 알림이 붙었나).
  --within N(1 이상)이면 같은 상황 뒤 N턴 안에서 본다(예: 다음 사용자 글이 되묻는 말인가).
  그 사이에 같은 상황이 또 오면 거기까지만 본다. 재발 하나를 두 번 세지 않기 위해서다.
- --per session 이면 세션 단위로 센다. 같은 상황이 한 번이라도 온 세션 수와 그 가운데 재발이 있던 세션 수다.
- --since, --until 은 `YYYY-MM-DD` 나 `YYYY-MM-DDTHH:MM` 이고 이 컴퓨터의 시간대다. --until 에 날짜만 주면 그날 끝까지다.
  같은 상황으로 걸린 글의 시각이 이 사이에 있어야 센다. 재발은 --until 뒤에 나온 것도 본다.

빼는 것과 한 번만 세는 것
- 예약 작업 세션은 뺀다. 서브에이전트 기록(세션 폴더 아래의 파일)과 서브에이전트 안쪽 대화는 읽지 않는다.
- 이어 연 세션에는 앞 세션의 줄이 같은 uuid로 복사돼 있다. 같은 uuid의 턴은 한 번만 센다.
  재발은 어느 쪽 파일에서 나왔든 그 턴의 재발로 친다.
- 무엇이 사람이 친 글이고 무엇이 에이전트가 보인 글인지는 기록 스크립트(session_extract.py)의 판정을 그대로 쓴다.
- 찍는 글은 첫 80자다. 걸린 곳이 그 뒤에 있으면 걸린 곳 둘레도 찍는다. 비밀값 모양이 보이면 글을 가린다.

세션 기록은 --projects-dir, 없으면 <Claude 설정 폴더>/projects 에서 읽는다.
"""
import argparse, datetime, importlib.util, json, os, pathlib, re, sys

SHOW = 80
PLACES = ("user", "agent", "skill", "hook")
HOOK_EVENT = "UserPromptSubmit"
MASKED = "[비밀값이 있어 가림]"
SLASH_RE = re.compile(r"^/([A-Za-z][\w-]*(?::[\w-]+)?)(?=\s|$)")
SKILL_LINE = "- Skill: "
TRIAL_FIELDS = ("상태", "종류", "볼 날짜", "셀 것")
HYPOTHESES = ("evolve", "hypotheses.md")


def fail(message):
    sys.stderr.write(message + "\n")
    sys.exit(1)


def load_sibling(name, path):
    if not path.is_file():
        fail(f"스크립트를 못 찾음: {path}")
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_measure():
    """측정 스크립트. 예약 작업 세션을 가르는 방법과 기록 스크립트를 읽는 방법을 빌려 쓴다."""
    return load_sibling("measure", pathlib.Path(__file__).resolve().parent / "measure.py")

# ---------------------------------------------------------------------------
# 때
# ---------------------------------------------------------------------------

def parse_when(value, end=False):
    try:
        if len(value) == 10:
            day = datetime.date.fromisoformat(value)
            moment = datetime.datetime.combine(day + datetime.timedelta(days=1) if end else day, datetime.time())
        else:
            moment = datetime.datetime.fromisoformat(value)
    except ValueError:
        fail(f"때는 YYYY-MM-DD 나 YYYY-MM-DDTHH:MM 으로 적는다: {value}")
    return moment.astimezone()


def moment_of(timestamp):
    if not isinstance(timestamp, str) or not timestamp:
        return None
    try:
        moment = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment.astimezone()


def show_time(timestamp):
    moment = moment_of(timestamp)
    return moment.strftime("%Y-%m-%d %H:%M:%S") if moment else "----"

# ---------------------------------------------------------------------------
# 세션 기록을 턴으로 읽기
# ---------------------------------------------------------------------------

def unquote(lines):
    return "\n".join(line[2:] if line.startswith("> ") else "" if line == ">" else line for line in lines)


def hook_text(attachment):
    if not isinstance(attachment, dict) or not str(attachment.get("type") or "").startswith("hook_"):
        return None
    if attachment.get("hookEvent") != HOOK_EVENT:
        return None
    content = attachment.get("content")
    if not isinstance(content, str) or not content.strip():
        content = attachment.get("stdout")
    return content.strip() if isinstance(content, str) and content.strip() else None


def new_turn(key, timestamp, text):
    turn = {"key": key, "user": [], "agent": [], "skill": [], "hook": []}
    if text is not None:
        turn["user"].append((timestamp, text))
        named = SLASH_RE.match(text)
        if named:
            turn["skill"].append((timestamp, named.group(1)))
    return turn


def read_session(path, extractor, measure):
    """세션 기록 파일 하나를 (턴 목록, 예약 작업인가)로 읽는다. 턴의 칸마다 [(시각, 글)]이다."""
    sid = pathlib.Path(path).name[:-len(".jsonl")]
    turns, scheduled = [new_turn((sid, "start"), None, None)], False
    try:
        handle = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return [], False
    with handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except ValueError:
                continue
            if not isinstance(data, dict) or data.get("isSidechain"):
                continue
            kind, stamp = data.get("type"), data.get("timestamp")
            if kind == "user":
                message = data.get("message")
                if measure.is_scheduled(data, message.get("content") if isinstance(message, dict) else None):
                    scheduled = True
            if kind == "attachment":
                noted = hook_text(data.get("attachment"))
                if noted:
                    turns[-1]["hook"].append((stamp, noted))
                    continue
            if kind not in ("user", "assistant", "attachment"):
                continue
            try:
                groups = extractor.classify(data)
            except extractor.UnknownFormat:
                continue
            for who, lines in groups:
                if who == "사용자":
                    turns.append(new_turn(data.get("uuid") or (sid, len(turns)), stamp, unquote(lines)))
                elif who == "에이전트":
                    turns[-1]["agent"].append((stamp, unquote(lines)))
                elif who == "도구":
                    for item in lines:
                        if item.startswith(SKILL_LINE):
                            turns[-1]["skill"].append((stamp, item[len(SKILL_LINE):].strip()))
    return turns, scheduled


def session_paths(projects):
    """<projects>/*/<세션 id>.jsonl. 더 깊은 폴더(서브에이전트 기록)는 보지 않는다."""
    if not projects.is_dir():
        return []
    return sorted(path for folder in sorted(projects.iterdir()) if folder.is_dir() for path in folder.glob("*.jsonl"))


def read_sessions(projects, extractor, measure, floor=None, only=None):
    """[(세션 id, 턴 목록)]과 뺀 예약 작업 세션 수. floor 보다 전에 마지막으로 고친 파일은 읽지 않는다."""
    sessions, skipped = [], 0
    for path in session_paths(projects):
        sid = path.name[:-len(".jsonl")]
        if only and not sid.startswith(only):
            continue
        try:
            if floor is not None and path.stat().st_mtime < floor.timestamp():
                continue
        except OSError:
            continue
        turns, scheduled = read_session(path, extractor, measure)
        if scheduled:
            skipped += 1
        else:
            sessions.append((sid, turns))
    return sessions, skipped

# ---------------------------------------------------------------------------
# 조건
# ---------------------------------------------------------------------------

def parse_condition(spec):
    place, sep, pattern = spec.partition(":")
    absent = place.startswith("!")
    place = place.lstrip("!")
    if not sep or place not in PLACES or not pattern:
        fail(f"조건은 <어디>:<정규식> 꼴이고 어디는 {', '.join(PLACES)} 가운데 하나다: {spec}")
    try:
        return {"place": place, "absent": absent, "re": re.compile(pattern), "spec": spec}
    except re.error as error:
        fail(f"정규식이 틀림({error}): {spec}")


def match_turn(turn, conditions):
    """모든 조건이 맞으면 걸린 글 [(어디, 시각, 글, 걸린 자리)], 아니면 None. 없어야 맞는 조건은 글을 내지 않는다."""
    hits = []
    for cond in conditions:
        found = None
        for stamp, text in turn[cond["place"]]:
            m = cond["re"].search(text)
            if m:
                found = (cond["place"], stamp, text, m.span())
                break
        if cond["absent"]:
            if found:
                return None
        elif not found:
            return None
        else:
            hits.append(found)
    if not hits:   # 없어야 맞는 조건뿐이면 그 턴의 사용자 글을 보여 준다
        hits = [("user", stamp, text, (0, 0)) for stamp, text in turn["user"][:1]] or [("user", None, "", (0, 0))]
    return hits


def count(sessions, same, recur, within, since, until):
    """{턴 키: {session, hit, recur}}. 같은 uuid의 턴은 처음 본 세션의 것으로 한 번만 담는다."""
    found = {}
    for sid, turns in sessions:
        marks = [match_turn(turn, same) for turn in turns]
        spots = [index for index, hit in enumerate(marks) if hit]
        for order, index in enumerate(spots):
            hit = marks[index][0]
            when = moment_of(hit[1])
            if when is None or when < since or (until and when >= until):
                continue
            entry = found.setdefault(turns[index]["key"], {"session": sid, "hit": hit, "recur": {}})
            if not recur:
                continue
            if within == 0:
                window = [index]
            else:
                stop = spots[order + 1] if order + 1 < len(spots) else len(turns) - 1
                window = range(index + 1, min(index + within, stop) + 1)
            for later in window:
                again = match_turn(turns[later], recur)
                if again:
                    entry["recur"].setdefault(turns[later]["key"], (sid, again[0]))
                    break
    return found

# ---------------------------------------------------------------------------
# 찍기
# ---------------------------------------------------------------------------

def one_line(text):
    return " ".join(text.split())


def shown(text, span, find_secret):
    line = one_line(text)
    if find_secret(text):
        return MASKED
    out = line[:SHOW]
    lead = len(one_line(text[:span[0]]))
    if span[1] > span[0] and lead >= SHOW:
        out += " … 걸린 곳: " + one_line(text[max(0, span[0] - 20):span[1] + 20])[:SHOW]
    return out


def hit_line(label, sid, hit, find_secret):
    place, stamp, text, span = hit
    return f"[{label}] {sid} {show_time(stamp)} {place} | {shown(text, span, find_secret)}"


def cmd_count(a):
    if a.within < 0:
        fail("--within 은 0 이상")
    same = [parse_condition(spec) for spec in a.same]
    recur = [parse_condition(spec) for spec in a.recur]
    since, until = parse_when(a.since), parse_when(a.until, end=True) if a.until else None
    measure = load_measure()
    extractor = measure.load_extractor()
    projects = pathlib.Path(a.projects_dir).expanduser() if a.projects_dir else measure.claude_dir() / "projects"
    sessions, skipped = read_sessions(projects, extractor, measure, floor=since, only=a.session)
    found = count(sessions, same, recur, a.within, since, until)
    entries = sorted(found.values(), key=lambda entry: (entry["hit"][1] or "", entry["session"]))
    if a.per == "session":
        by_session = {}
        for entry in entries:
            by_session.setdefault(entry["session"], []).append(entry)
        total = len(by_session)
        again = sum(1 for group in by_session.values() if any(entry["recur"] for entry in group))
    else:
        total, again = len(entries), sum(1 for entry in entries if entry["recur"])
    unit = "세션" if a.per == "session" else "턴"
    summary = f"같은 상황 {total}번 중 재발 {again}번" if recur else f"같은 상황 {total}번"
    if a.json:
        rows = [{"session": entry["session"], "time": show_time(entry["hit"][1]), "where": entry["hit"][0],
                 "text": shown(entry["hit"][2], entry["hit"][3], extractor.find_secret),
                 "recur": [{"session": sid, "time": show_time(hit[1]), "where": hit[0],
                            "text": shown(hit[2], hit[3], extractor.find_secret)} for sid, hit in entry["recur"].values()]}
                for entry in entries]
        print(json.dumps({"unit": unit, "same": total, "recur": again if recur else None, "sessions_read": len(sessions),
                          "scheduled_skipped": skipped, "hits": rows}, ensure_ascii=False, indent=2))
        return
    print(f"기간: {since.strftime('%Y-%m-%d %H:%M')} ~ {until.strftime('%Y-%m-%d %H:%M') if until else '지금'}"
          f" | 읽은 세션 {len(sessions)}개, 뺀 예약 작업 세션 {skipped}개 | 단위: {unit}")
    print("같은 상황: " + " 그리고 ".join(cond["spec"] for cond in same))
    if recur:
        where = "같은 턴" if a.within == 0 else f"뒤 {a.within}턴 안"
        print("재발: " + " 그리고 ".join(cond["spec"] for cond in recur) + f" ({where})")
    for entry in entries:
        print(hit_line("같은 상황", entry["session"], entry["hit"], extractor.find_secret))
        for sid, hit in entry["recur"].values():
            print("  " + hit_line("재발", sid, hit, extractor.find_secret))
    print(summary)

# ---------------------------------------------------------------------------
# due
# ---------------------------------------------------------------------------

def read_trials(text):
    """추정 기록의 시도들. [{group, title, 상태, 종류, 볼 날짜, 셀 것, 결과: [..]}]"""
    trials, group, trial, fenced = [], "", None, False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if fenced:
            continue
        if line.startswith("## "):
            group, trial = line[3:].strip(), None
        elif line.startswith("### "):
            trial = {"group": group, "title": line[4:].strip(), "결과": []}
            trials.append(trial)
        elif trial is not None and line.startswith("- "):
            name, sep, value = line[2:].partition(":")
            if sep and name.strip() == "결과":
                trial["결과"].append(value.strip())
            elif sep and name.strip() in TRIAL_FIELDS:
                trial[name.strip()] = value.strip()
    return trials


def cmd_due(a):
    if not a.knowledge_base:
        fail("지식 베이스를 모른다. 인자로 주거나 KNOWLEDGE_BASE_DIR 을 둔다")
    try:
        today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    except ValueError:
        fail(f"날짜는 YYYY-MM-DD로 적는다: {a.today}")
    path = pathlib.Path(a.knowledge_base).expanduser().joinpath(*HYPOTHESES)
    total = 0
    for trial in read_trials(path.read_text(encoding="utf-8")) if path.is_file() else []:
        if not trial.get("상태", "").startswith("지켜보는 중"):
            continue
        try:
            day = datetime.date.fromisoformat(trial.get("볼 날짜", "")[:10])
        except ValueError:
            day = None
        if day is not None and day > today:
            continue
        total += 1
        print(" | ".join([trial["group"], trial["title"], f"볼 날짜: {day.isoformat() if day else '없음'}",
                          f"종류: {trial.get('종류') or '없음'}", f"셀 것: {trial.get('셀 것') or '없음'}",
                          f"결과 줄 {len(trial['결과'])}개"]))
    print(f"합계 {total}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("count")
    c.add_argument("--since", required=True)
    c.add_argument("--until")
    c.add_argument("--same", action="append", required=True)
    c.add_argument("--recur", action="append", default=[])
    c.add_argument("--within", type=int, default=0)
    c.add_argument("--per", choices=("turn", "session"), default="turn")
    c.add_argument("--session")
    c.add_argument("--json", action="store_true")
    c.add_argument("--projects-dir")
    c.set_defaults(run=cmd_count)
    d = sub.add_parser("due")
    d.add_argument("knowledge_base", nargs="?", default=os.environ.get("KNOWLEDGE_BASE_DIR"))
    d.add_argument("--today")
    d.set_defaults(run=cmd_due)
    a = ap.parse_args()
    a.run(a)


if __name__ == "__main__":
    main()
