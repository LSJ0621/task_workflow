#!/usr/bin/env python3
"""지식 베이스의 불변 조건을 점검한다.
사용: check_invariants.py <지식 베이스> [--skip-rule-cases] [--skip-summary]
        [--claude-dir <폴더>] [--plugin-dir <폴더>] [--today YYYY-MM-DD] [--board-lag-days <일>]
종료 코드 0 = 통과. 출력은 "문제"와 "알림" 두 가지다. 문제가 있으면 종료 코드 1이고, 알림은 종료 코드를 바꾸지 않는다.

문제로 보는 것: 식별자 중복 없음, 모든 원본에 id·date·status 머리말, 결정에 이유 절,
본문의 모든 C-·D-·X-·R- id 참조가 존재, superseded 쌍 일관,
사례·결정·맥락에 scope(me 또는 project:<이름>) 있음(raw/archive/ 아래는 예전 기록이라 건너뜀),
wiki/context.md가 있으면 유효한 결정·맥락 id가 wiki/context.md나 wiki/projects/*.md 어딘가에 있음
(머리말 snapshot: true 인 맥락은 그날의 상태라 건너뜀),
규칙별 사례표(evolve/rule-cases.md, 없으면 예전 위치 wiki/rule-cases.md)가 있으면 표 머리가 지금 형식이고 모든 사례가 표에 있음.
status 는 draft | active | superseded | archived 다(예전 기록에는 rejected 도 있다).
요약과 카드(wiki/context.md, wiki/projects/*.md)에는 active 인 기록만 올린다. active 가 아닌 사례·결정·맥락의 id가 거기 있으면 문제다.
status: draft 인 기록은 확인 전이라 "요약에 나와야 한다"와 "사례표에 있어야 한다" 검사에서 뺀다.
status: draft 인 결정은 "결정에 이유 절" 검사에서도 뺀다. 뽑지 못한 기록은 요지가 "아직 없음"이라서다. active 가 되면 본다.
status: archived 는 보관한 기록이다. 요약에 나오지 않아도 되고, archived_reason 이 done | in-rules | project-doc | expired 중 하나여야 한다.
archived_reason 이 in-rules 나 project-doc 이면 moved_to(지금 그 내용이 있는 위치)가 있어야 한다.
valid_until 이 있으면 YYYY-MM-DD 여야 한다.
이유 절은 예전 형식 "## 이유", 새 틀의 "### 이유"("## 요지" 아래), 구조 결정 기록의 "## 이유와 근거"를 모두 알아본다.
머리말에 source 가 있으면 session, memo, agent 중 하나여야 한다. source: session 이면 session·range 가 "-"가 아니고
본문에 <!-- extract:start --> 와 <!-- extract:end --> 가 하나씩 순서대로 있어야 한다.
표시 사이가 "발췌: raw/sessions/<세션 id>.md <범위>" 줄로 시작하는 새 형식 기록은 그 파일과 그 범위 묶음이 있어야 한다.
source: agent 는 자가 발전이 스스로 정한 구조 결정 기록(type: decision, tags에 structure)에만 쓴다.
source 가 없는 예전 기록은 이 검사를 하지 않는다. omitted, memo 칸은 있어도 되고 없어도 된다.
--skip-rule-cases 를 주면 "모든 사례가 표에 있음" 검사만 건너뛴다. 사례를 분류하기 전에 도는 점검(새벽 1단계 기록, 구조 점검, 사용자 분석)이 쓴다.
새 사례는 자가 발전(analyze-context)이 분류하기 전이라 표에 없는 게 맞아서다. 표 머리와 줄 형식은 그대로 본다.
--skip-summary 를 주면 "유효한 결정·맥락이 요약이나 카드에 나온다" 검사만 건너뛴다. 정리(4단계)보다 먼저 도는 점검(새벽 1단계 기록, 3단계 분석)이 쓴다.
새로 확정된 결정·맥락은 정리가 올리기 전이라 요약에 없는 게 맞아서다. active 가 아닌 기록이 요약에 올라가 있는지는 그대로 본다.
두 옵션은 함께 줄 수 있다. 옵션 없이 돌리면 전부 본다. 정리(4단계)가 그렇게 돌린다.
raw/reviews/ 의 점검 보고서(HTML), raw/reports/ 의 예전 아침 보고서, raw/sessions/ 의 세션 발췌는 머리말과 식별자가 없는 파일이라 머리말 점검에서 뺀다
(raw/archive/ 아래는 예전 기록이라 그대로 본다).
메모(raw/journal/)와 세션 발췌(raw/sessions/)는 대화를 옮긴 재료라 id 참조 점검에서 뺀다.
그 밖의 문서(evolve/ 의 추정 기록과 사례표, 예전 아침 보고서 포함)에 적힌 C-·D-·X- id 참조는 존재하는지 본다. H- 번호는 기록 id가 아니라 보지 않는다.
P-로 시작하는 옛 기준 항목 id는 없어진 기준 문서의 이름이라 지난 기록에 남아 있어도 점검하지 않는다.

알림으로 내는 것(종료 코드를 바꾸지 않는다. 토요일 구조 점검이 처리한다):
- 실제 대조: 요약·카드·상황판에 백틱으로 적힌 스킬·서브에이전트·훅·예약 작업·스크립트 이름이 실제로 있는지.
  이름 앞에 종류를 적은 것("예약 작업 `이름`", "스킬(`이름`)")과 모양으로 아는 것(`<플러그인>:<스킬>`, `*.py`, `*.sh`)만 본다.
  실제 목록은 플러그인 폴더(--plugin-dir, 기본은 이 스크립트가 든 플러그인)와 Claude 설정 폴더(--claude-dir, 기본 $CLAUDE_CONFIG_DIR 또는 ~/.claude)에서 읽는다.
- 기한 지남: valid_until 이 오늘(--today, 기본 오늘)보다 앞인 active 기록.
- 상황판 날짜: 상황판 묶음의 "고친 날짜"보다 그 프로젝트 카드에 적힌 저장소의 최근 커밋이 --board-lag-days(기본 3)일 넘게 뒤일 때.
  지식 베이스 자신의 묶음은 메모와 기록 커밋이 매일 쌓이므로 INDEX.md, CLAUDE.md, README.md, tests/, work/ 를 건드린 커밋만 센다."""
import datetime, os, pathlib, re, subprocess, sys

ID_RE = re.compile(r"\b([CDXR]-\d{8}-\d{2})\b")
SCOPE_RE = re.compile(r"^(me|project:[A-Za-z0-9][A-Za-z0-9._-]*)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RECORD_TYPES = {"case", "decision", "context"}
RECORD_DIRS = {"cases": "case", "decisions": "decision", "context": "context"}
TABLE_HEAD = ["사례", "한 줄 요약", "관련 규칙", "규칙과 관계"]
RELATIONS = {"규칙을 뒷받침", "규칙과 반대", "규칙 없음", "기각"}

USAGE = ("사용: check_invariants.py <지식 베이스> [--skip-rule-cases] [--skip-summary] "
         "[--claude-dir <폴더>] [--plugin-dir <폴더>] [--today YYYY-MM-DD] [--board-lag-days <일>]")
FLAGS = {"--skip-rule-cases", "--skip-summary"}
VALUE_OPTIONS = {"--claude-dir", "--plugin-dir", "--today", "--board-lag-days"}
NO_FRONTMATTER_DIRS = {"journal", "reviews", "reports", "sessions"}   # raw/ 바로 아래에서 머리말 없이 쌓는 폴더
NO_ID_CHECK_DIRS = {"journal", "sessions"}   # 대화를 옮긴 재료. 없는 id가 적혀 있어도 된다
SOURCES = {"session", "memo", "agent"}
ARCHIVED_REASONS = {"done", "in-rules", "project-doc", "expired"}
MOVED_REASONS = {"in-rules", "project-doc"}
EXTRACT_START = "<!-- extract:start -->"
EXTRACT_END = "<!-- extract:end -->"
EXCERPT_LINE_RE = re.compile(r"^발췌: (raw/sessions/[^\s/]+\.md) (\S+\.\.\S+)$")
RANGE_START_RE = re.compile(r"^<!-- range:start (\S+\.\.\S+)(?: omitted:\S+)? -->$", re.M)
REASON_RE = re.compile(r"^#{2,3} 이유", re.M)   # "## 이유", "### 이유", "## 이유와 근거"
RULE_CASES = ("evolve/rule-cases.md", "wiki/rule-cases.md")   # 지금 위치, 예전 위치

# 실제 대조. 이름 앞에 적힌 종류 말 → 종류
KIND_WORDS = {"스킬": "skill", "서브에이전트": "agent", "훅": "hook", "예약 작업": "scheduled", "스크립트": "script"}
KIND_NAMES = {"skill": "스킬", "agent": "서브에이전트", "hook": "훅", "scheduled": "예약 작업", "script": "스크립트"}
KIND_BEFORE_RE = re.compile(r"(스킬|서브에이전트|훅|예약 작업|스크립트)\s*\(?\s*`([^`\s]+)`")
BACKTICK_RE = re.compile(r"`([^`\s]+)`")
SCRIPT_SHAPE_RE = re.compile(r"^[\w./~-]+\.(py|sh)$")
PLAIN_NAME_RE = re.compile(r"^[A-Za-z0-9][\w.-]*$")
BOARD_DATE_RE = re.compile(r"^- 고친 날짜:\s*(\d{4}-\d{2}-\d{2})")
REPO_LINE_RE = re.compile(r"^- (?:저장소|위치):(.*)$", re.M)
KB_OWN_PATHS = ["INDEX.md", "CLAUDE.md", "README.md", "tests", "work"]
DEFAULT_BOARD_LAG_DAYS = 3

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

def tag_list(fm):
    return [t.strip().strip("\"'") for t in fm.get("tags", "").strip("[]").split(",") if t.strip()]

def check_source(fm, text, name, kb):
    """머리말 source 칸과 그에 딸린 session·range·표시를 본다. source 가 없으면 예전 기록이라 보지 않는다."""
    source = fm.get("source")
    if not source:
        return []
    if source not in SOURCES:
        return [f"source 값이 session, memo, agent 중 하나가 아님({source}): {name}"]
    if source == "agent":
        if fm.get("type") != "decision" or "structure" not in tag_list(fm):
            return [f"source: agent 는 구조 결정 기록(type: decision, tags에 structure)에만 쓴다: {name}"]
        return []
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
    else:
        found += check_excerpt(body, name, kb)
    return found

def check_excerpt(body, name, kb):
    """새 형식 기록은 표시 사이 첫 줄이 발췌 위치다. 그 파일에 그 범위 묶음이 있는지 본다. 예전 형식은 보지 않는다."""
    inside = body[body.index(EXTRACT_START) + len(EXTRACT_START):body.index(EXTRACT_END)]
    first = next((line for line in inside.splitlines() if line.strip()), "")
    m = EXCERPT_LINE_RE.match(first)
    if not m:
        return []
    path = kb / m.group(1)
    if not path.is_file():
        return [f"발췌 위치의 파일이 없음({m.group(1)}): {name}"]
    if m.group(2) not in RANGE_START_RE.findall(path.read_text(encoding="utf-8")):
        return [f"발췌 위치의 범위가 그 파일에 없음({m.group(1)} {m.group(2)}): {name}"]
    return []

def check_archived(fm, name):
    if fm.get("status") != "archived":
        return []
    reason = fm.get("archived_reason", "")
    if reason not in ARCHIVED_REASONS:
        return [f"archived 인데 archived_reason 이 done, in-rules, project-doc, expired 중 하나가 아님({reason or '없음'}): {name}"]
    if reason in MOVED_REASONS and not fm.get("moved_to"):
        return [f"archived_reason: {reason} 인데 moved_to 없음: {name}"]
    return []

# ---------------------------------------------------------------------------
# 알림
# ---------------------------------------------------------------------------

def names_in(folder, pattern, stem=False):
    if not folder.is_dir():
        return None
    return {(p.stem if stem else p.name) for p in folder.glob(pattern)}

def merged(*sets):
    """폴더가 하나도 없으면 None(볼 수 없음), 아니면 합친 이름들."""
    present = [s for s in sets if s is not None]
    return set().union(*present) if present else None

def inventory(plugin, claude):
    """종류마다 실제로 있는 이름들. 볼 폴더가 없으면 None이라 그 종류는 대조하지 않는다."""
    def skills(root):
        folder = root / "skills"
        return {p.parent.name for p in folder.glob("*/SKILL.md")} if folder.is_dir() else None
    def hook_names(root):
        folder = root / "hooks"
        if not folder.is_dir():
            return None
        return {n for p in folder.iterdir() if p.is_file() for n in (p.name, p.stem)}
    def scripts(root, patterns):
        if not root.is_dir():
            return None
        return {p.name for pattern in patterns for p in root.glob(pattern) if p.is_file()}
    tasks = claude / "scheduled-tasks"
    return {
        "skill": merged(skills(plugin), skills(claude)),
        "agent": merged(names_in(plugin / "agents", "*.md", True), names_in(claude / "agents", "*.md", True)),
        "hook": merged(hook_names(plugin), hook_names(claude)),
        "scheduled": {p.name for p in tasks.iterdir() if p.is_dir()} if tasks.is_dir() else None,
        "script": merged(scripts(plugin, ["**/*.py", "**/*.sh"]), scripts(claude / "bin", ["*"]),
                         scripts(claude / "hooks", ["*"])),
    }

def plugin_name(plugin):
    for manifest in (plugin / ".claude-plugin" / "plugin.json", plugin / "plugin.json"):
        if manifest.is_file():
            m = re.search(r'"name"\s*:\s*"([^"]+)"', manifest.read_text(encoding="utf-8"))
            if m:
                return m.group(1)
    return plugin.name

def named_things(line, plugin_label):
    """한 줄에서 (종류, 적힌 이름, 찾을 이름)을 뽑는다."""
    found = {}
    for m in KIND_BEFORE_RE.finditer(line):
        found[m.group(2)] = KIND_WORDS[m.group(1)]
    for token in BACKTICK_RE.findall(line):
        if token.startswith(plugin_label + ":"):
            found.setdefault(token, "skill")
        elif SCRIPT_SHAPE_RE.match(token):
            found[token] = "script"   # 앞에 "훅"이라고 적혀 있어도 파일 이름이면 스크립트로 찾는다
    for token, kind in found.items():
        name = token
        if kind == "script" or "/" in name:
            name = name.rstrip("/").split("/")[-1]
        if ":" in name:
            prefix, name = name.split(":", 1)
            if prefix != plugin_label:
                continue   # 다른 플러그인의 것은 여기서 볼 수 없다
        if PLAIN_NAME_RE.match(name):
            yield kind, token, name

def reality_notices(kb, plugin, claude):
    real = inventory(plugin, claude)
    label = plugin_name(plugin)
    notices, unseen = [], set()
    files = [kb / "wiki" / "context.md", kb / "wiki" / "board.md"] + sorted((kb / "wiki" / "projects").glob("*.md"))
    for path in files:
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for kind, token, name in named_things(line, label):
                names = real[kind]
                if names is None:
                    unseen.add(kind)
                    continue
                candidates = {name}
                if kind == "script":
                    candidates |= {name + ".py", name + ".sh"}   # 확장자 없이 적은 이름
                if kind == "hook" and real["script"]:
                    names = names | real["script"]   # 훅을 스크립트 파일 이름으로 적은 것
                if not candidates & names:
                    notices.append(f"실제 대조: {path.relative_to(kb)}:{number} {KIND_NAMES[kind]} `{token}` 없음")
    for kind in sorted(unseen):
        notices.append(f"실제 대조: {KIND_NAMES[kind]} 목록을 읽을 폴더가 없어 대조하지 못함")
    return notices

def expiry_notices(expiring, today):
    notices = []
    for i, (until, name) in sorted(expiring.items()):
        if DATE_RE.match(until) and until < today.isoformat():
            notices.append(f"기한 지남: {i} valid_until {until} ({name})")
    return notices

def last_commit_date(repo, paths=None):
    try:
        done = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%cs", "--"] + (paths or []),
                              capture_output=True, text=True)
    except OSError:
        return None
    value = done.stdout.strip()
    return value if done.returncode == 0 and DATE_RE.match(value) else None

def card_repo(card):
    """카드의 저장소 줄에 백틱으로 적힌 첫 경로(~/ 나 / 로 시작)."""
    if not card.is_file():
        return None
    for m in REPO_LINE_RE.finditer(card.read_text(encoding="utf-8")):
        for token in BACKTICK_RE.findall(m.group(1)):
            if token.startswith(("~/", "/")):
                return pathlib.Path(token).expanduser()
    return None

def board_notices(kb, lag_days):
    board = kb / "wiki" / "board.md"
    if not board.is_file():
        return []
    notices, name = [], None
    for line in board.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            continue
        m = BOARD_DATE_RE.match(line)
        if not (m and name):
            continue
        repo = card_repo(kb / "wiki" / "projects" / f"{name}.md")
        if repo is None or not repo.is_dir():
            continue
        own = repo.resolve() == kb.resolve()
        latest = last_commit_date(repo, KB_OWN_PATHS if own else None)
        if not latest:
            continue
        gap = (datetime.date.fromisoformat(latest) - datetime.date.fromisoformat(m.group(1))).days
        if gap > lag_days:
            notices.append(f"상황판 날짜: {name} 묶음 고친 날짜 {m.group(1)}, 저장소 최근 커밋 {latest}({gap}일 뒤)")
    return notices

# ---------------------------------------------------------------------------

def parse_args(argv):
    flags, values, paths = set(), {}, []
    position = 0
    while position < len(argv):
        a = argv[position]
        if a in VALUE_OPTIONS:
            if position + 1 >= len(argv):
                sys.exit(USAGE)
            values[a] = argv[position + 1]
            position += 2
            continue
        if a.startswith("--"):
            if a not in FLAGS:
                sys.exit(USAGE)
            flags.add(a)
        else:
            paths.append(a)
        position += 1
    if len(paths) != 1:
        sys.exit(USAGE)
    try:
        today = datetime.date.fromisoformat(values["--today"]) if "--today" in values else datetime.date.today()
        lag = int(values.get("--board-lag-days", DEFAULT_BOARD_LAG_DAYS))
    except ValueError:
        sys.exit(USAGE)
    claude = pathlib.Path(values.get("--claude-dir") or os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude").expanduser()
    plugin = (pathlib.Path(values["--plugin-dir"]).expanduser() if "--plugin-dir" in values
              else pathlib.Path(__file__).resolve().parents[3])
    return pathlib.Path(paths[0]).expanduser(), flags, claude, plugin, today, lag

def main():
    kb, flags, claude, plugin, today, lag = parse_args(sys.argv[1:])
    skip_rule_cases = "--skip-rule-cases" in flags
    skip_summary = "--skip-summary" in flags
    problems = []
    ids = {}
    case_ids = set()
    not_active = {}  # active 가 아닌 사례·결정·맥락 id → status. 요약에 올라가 있으면 안 된다
    summarize = {}   # 요약에 나와야 하는 유효한 결정·맥락 id → 파일 이름
    expiring = {}    # valid_until 이 있는 active 기록 id → (날짜, 파일 이름)
    # 메모(raw/journal/), 점검 보고서(raw/reviews/), 예전 아침 보고서(raw/reports/), 세션 발췌(raw/sessions/)는 머리말이 없는 파일이다.
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
        status = fm.get("status")
        if i:
            if i in ids: problems.append(f"식별자 중복: {i} ({p.name}, {ids[i]})")
            ids[i] = p.name
            if not p.name.startswith(i): problems.append(f"파일명이 id로 시작하지 않음: {p.name}")
            # 확인 전 사례는 자가 발전이 읽지 않으므로 사례표에 없어도 된다.
            if fm.get("type") == "case" and status != "draft": case_ids.add(i)
        # 사례·결정·맥락만 scope와 요약을 본다. raw/archive/ 아래 예전 기록은 건너뛴다.
        rel = p.relative_to(kb).parts
        kind = fm.get("type") or (RECORD_DIRS.get(rel[1]) if len(rel) > 2 else None)
        if kind in RECORD_TYPES and "archive" not in rel[:2]:
            scope = fm.get("scope")
            if not scope:
                problems.append(f"머리말 scope 없음: {p.relative_to(kb)}")
            elif not SCOPE_RE.match(scope):
                problems.append(f"scope 값이 me나 project:<이름>이 아님({scope}): {p.relative_to(kb)}")
            if (kind in ("decision", "context") and status == "active" and i
                    and fm.get("snapshot", "").lower() != "true"):
                summarize[i] = p.name
            if status and status != "active" and i:
                not_active[i] = status
            until = fm.get("valid_until", "").strip("\"'")
            if until and not DATE_RE.match(until):
                problems.append(f"valid_until 값이 YYYY-MM-DD가 아님({until}): {p.name}")
            elif until and status == "active" and i:
                expiring[i] = (until, p.name)
            problems += check_source(fm, text, p.name, kb)
            problems += check_archived(fm, p.name)
        # 확인 전(draft) 결정은 뽑지 못해 요지가 비어 있을 수 있어 이유 절을 보지 않는다. active가 되면 본다.
        if fm.get("type") == "decision" and status != "draft" and not REASON_RE.search(text):
            problems.append(f"결정에 이유 절 없음: {p.name}")
        if status == "superseded" and not fm.get("superseded_by"):
            problems.append(f"superseded 인데 superseded_by 없음: {p.name}")
    # 메모와 세션 발췌는 대화를 옮긴 재료라 id 참조 점검에서 뺀다. 숨김 폴더(.git, .claude 등)도 뺀다.
    for p in kb.glob("**/*.md"):
        rel = p.relative_to(kb).parts
        if any(x.startswith(".") for x in rel): continue
        if rel[0] == "raw" and len(rel) > 1 and rel[1] in NO_ID_CHECK_DIRS: continue
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
        for i in sorted(set(not_active) & shown):
            if not_active[i] == "draft":
                problems.append(f"확인 전(draft) 기록이 요약(wiki/context.md, wiki/projects/)에 올라가 있음: {i}")
            else:
                problems.append(f"active 가 아닌({not_active[i]}) 기록이 요약(wiki/context.md, wiki/projects/)에 올라가 있음: {i}")
    tables = [kb / t for t in RULE_CASES if (kb / t).is_file()]
    if len(tables) > 1:
        problems.append("규칙별 사례표가 두 곳에 있음: " + ", ".join(RULE_CASES))
    table = tables[0] if tables else None
    rows = 0
    if table:
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
    notices = reality_notices(kb, plugin, claude) + expiry_notices(expiring, today) + board_notices(kb, lag)
    print(f"점검 대상: {kb} · 원본 {len(raw_files)}개, 점검 보고서 {len(reports)}개, 규칙별 사례표 "
          + (f"{rows}줄" if table else "없음")
          + (" (표에 없는 사례 검사는 건너뜀)" if skip_rule_cases else "")
          + (" (요약에 없는 기록 검사는 건너뜀)" if skip_summary else ""))
    for x in notices: print("  [알림]", x)
    if notices: print(f"  알림 {len(notices)}건 (종료 코드에 넣지 않음)")
    for x in problems: print("  [문제]", x)
    print("  통과" if not problems else f"  문제 {len(problems)}건")
    sys.exit(0 if not problems else 1)

if __name__ == "__main__":
    main()
