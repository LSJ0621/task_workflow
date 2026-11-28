#!/usr/bin/env python3
"""세션 기록과 저장소에서 주 단위 숫자를 뽑아 지식 베이스의 evolve/metrics.md 를 고친다.

사용: measure.py [<지식 베이스>] [--weeks <주 수>] [--today YYYY-MM-DD] [--json] [--no-write]
        [--projects-dir <폴더>] [--read-root <경로> ...] [--min-tools <개수>]
        [--rules-repo <저장소>] [--rule-files <경로> ...] [--plugin-repo <저장소>] [--limits <한도 파일>]

- 지식 베이스를 안 주면 $KNOWLEDGE_BASE_DIR 을 쓴다.
- 이번 주와 그 앞 주들을 합쳐 --weeks(기본 2)주를 다시 센다. 주는 월요일에 시작해 일요일에 끝난다. 날짜는 이 컴퓨터의 시간대다.
- 표에 같은 주의 줄이 있으면 덮어쓰고, 다시 세지 않은 주의 줄은 그대로 둔다.
- --json 을 주면 다시 센 주의 숫자를 JSON으로 표준 출력에 찍는다(파일도 고친다). --no-write 는 파일을 고치지 않는다.
- 종료 코드 0 성공, 1 사용법이나 환경 오류.

뽑는 숫자(주마다)
- messages        사람이 친 메시지 수. 예약 작업 세션은 뺀다. 서브에이전트 안쪽 대화, 도구 결과, 시스템이 끼워 넣은 글은 세지 않는다.
                  무엇이 사람이 친 글인지는 기록 스크립트(session_extract.py)의 판정을 그대로 쓴다. 이어 연 세션에 복사된 같은 줄은 한 번만 센다.
- cases           새 사례 수(지적). raw/cases/ 에서 date 가 그 주인 사례. tags에 notfound 가 있는 것(못 찾음)은 뺀다.
- cases_per_100   메시지 100건당 지적 수.
- work_sessions   작업 세션 수. 그 주에 시작했고, 예약 작업이 아니고, 지식 베이스 폴더에서 연 세션이 아니고,
                  도구를 --min-tools(기본 10)번 이상 부른 세션. 서브에이전트가 부른 도구도 그 세션의 것으로 센다.
- read_index, read_summary, read_card, read_raw
                  작업 세션 가운데 색인(INDEX.md), 요약(wiki/context.md), 카드(wiki/projects/*.md),
                  원본(raw/cases, raw/decisions, raw/context)을 읽은 세션의 비율(%). Read, Grep, 그리고 cat·grep 같은 읽는 셸 명령을 본다.
- rule_chars      늘 읽히는 규칙 파일의 글자 수. 그 주 끝(이번 주는 지금) 기본 브랜치에 커밋된 내용이다. {경로: 글자 수}
- plugin_md_chars 플러그인 폴더의 md 전체 글자 수. 같은 시점이다. 플러그인 저장소를 못 찾으면 이번 주만
                  이 스크립트가 든 플러그인 폴더(설치본)에서 세고 지난 주는 비운다.
- evolve_commits  자가 발전 커밋 수. 규칙 저장소와 플러그인 저장소에서 그 주에 한 커밋 가운데 메시지에
                  "누가 정했는지: 자가 발전"(예전 문구 "누가 정했나:"도 본다)으로 시작하는 줄이 있고
                  규칙 문서(위 규칙 파일, 플러그인의 md)를 건드린 것. 문장 가운데에 그 말이 나오는 것은 세지 않는다.
                  두 저장소 가운데 하나라도 못 찾으면 비운다. 한쪽만 센 수를 전체처럼 적지 않기 위해서다.
- evolve_shrinking 그중 건드린 규칙 문서의 글자 수 합이 줄어든 커밋 수.
- memo_lines      메모 줄 수. raw/journal/ 의 그 주 날짜 파일에서 `HH:MM | `로 시작하는 줄.
읽을 수 없는 값(저장소가 없다 같은 것)은 표에 `-`, JSON에 null 로 적는다.

쓰임 표(evolve/usage.md)도 함께 고친다. 위 표의 열은 다른 스킬이 이름으로 읽어서 건드리지 않고 파일을 따로 둔다.
같은 주를 다시 세어 덮어쓰고, JSON에는 "usage" 로 따로 싣는다. 주마다 아래를 센다.
- reasks, bare_corrections, collected_days
                  새벽 작업이 모은 말(evolve/signals/YYYY-MM-DD.md, collect_signals.py 가 쓴다)의 그 주 날짜 파일에서 센다.
                  다시 물어본 말 수, 메모도 기록도 없는 지적 수, 목록이 있는 날 수. 목록이 하나도 없는 주는 앞의 둘을 비운다.
- stale_board     상황판(wiki/board.md)에서 고친 날짜가 그 주의 센 마지막 날보다 14일 넘게 앞선 묶음 수.
                  이번 주는 지금 파일에서, 지난 주는 그 주 끝에 지식 베이스에 커밋되어 있던 상황판에서 센다.
- skill_runs      {스킬 이름: Skill 도구로 부른 횟수}. 사람과 대화한 세션(예약 작업이 아닌 세션)에서 센다.
                  서브에이전트가 부른 것도 센다. 이어 연 세션에 복사된 같은 호출은 한 번만 센다.
- skill_runs_scheduled
                  {스킬 이름: 그 스킬을 쓴 예약 작업 세션 수}. 그 주에 시작한 예약 작업 세션마다, Skill 도구로 불렀거나
                  이 플러그인 스킬의 지침 파일(skills/<스킬>/SKILL.md, skills/<스킬>/references/ 아래)을 Read 로 읽었으면
                  한 번으로 센다. 예약 작업은 서브에이전트에 지침 파일의 경로를 넘겨 스킬을 돌려서 Skill 도구로는 안 잡힌다.
                  다른 스킬이 참조로 읽은 것도 들어가므로 실제보다 많이 잡힐 수 있다.
- skills_unused   이 스크립트가 든 플러그인의 스킬 가운데 그 주에 위 둘 어디에도 없는 것.
- skill_desc_chars, skill_count
                  플러그인 스킬들의 SKILL.md 머리말 description 글자 수의 합과 스킬 수. 그 주 끝(이번 주는 지금)
                  플러그인 저장소의 기본 브랜치에 커밋된 내용이다. 스킬의 본문과 참조 문서는 부를 때만 읽히고
                  description 은 세션마다 읽힌다. 플러그인 저장소를 못 찾으면 이번 주만 이 스크립트가 든
                  플러그인 폴더(설치본)에서 세고 지난 주는 비운다.

경로는 인자나 환경 변수로 받는다. 스크립트에 개인 경로를 적지 않는다.
- 세션 기록: --projects-dir, 없으면 <Claude 설정 폴더>/projects (Claude 설정 폴더는 $CLAUDE_CONFIG_DIR 또는 ~/.claude)
- 세션 기록에서 지식 베이스로 볼 경로: --read-root(여러 번 줄 수 있다), 없으면 지식 베이스의 실제 경로와 $KNOWLEDGE_BASE_DIR
- 규칙 저장소와 규칙 파일: --rules-repo 와 --rule-files, 없으면 한도 파일(--limits, $RULE_CHANGE_LIMITS,
  <Claude 설정 폴더>/evolve/limits.json)의 root 와 chars, 그것도 없으면 Claude 설정 폴더의 CLAUDE.md 와 output-styles/*.md
- 플러그인 저장소: --plugin-repo, 없으면 $PLUGIN_REPO_DIR, 없으면 지식 베이스의 플러그인 카드
  (wiki/projects/<플러그인 이름>.md)에 적힌 저장소 위치, 없으면 이 스크립트가 든 git 저장소.
  마지막 것은 그 저장소가 이 파일을 추적할 때만 쓴다. 설치본 폴더는 Claude 설정 저장소 안에 있어서,
  그냥 쓰면 설정 저장소가 플러그인 저장소로 잡히기 때문이다. 못 찾으면 표준 오류에 알린다.
"""
import argparse, collections, datetime, importlib.util, json, os, pathlib, re, subprocess, sys

HEADER = ["주", "메시지", "지적", "100건당 지적", "작업 세션", "색인 읽음", "요약 읽음", "카드 읽음", "원본 읽음",
          "전역 지침 글자", "응답 양식 글자", "플러그인 md 글자", "자가 발전 커밋", "줄어든 커밋", "메모 줄"]
INTRO = [
    "# 측정값",
    "",
    "`measure.py`(자가 발전 스킬의 스크립트)가 고쳐 쓴다. 손으로 고치지 않는다.",
    "주는 월요일에 시작해 일요일에 끝난다. 첫 칸의 날짜가 그 주의 월요일이고, `~` 뒤가 센 마지막 날이다.",
    "",
]
NOTES = [
    "",
    "## 세는 방법",
    "",
    "- 메시지: 사람이 친 메시지 수. 예약 작업 세션은 뺀다.",
    "- 지적: 그 주에 생긴 사례(`raw/cases/`) 수. 못 찾음(`notfound`) 사례는 뺀다. 100건당 지적은 메시지 100건당 지적 수다.",
    "- 작업 세션: 그 주에 시작한 세션 가운데 예약 작업도 아니고 지식 베이스 폴더에서 연 것도 아니며 도구를 10번 이상 부른 세션.",
    "- 색인·요약·카드·원본 읽음: 작업 세션 가운데 `INDEX.md`, `wiki/context.md`, `wiki/projects/*.md`, `raw/`의 사례·결정·맥락을 읽은 세션의 비율.",
    "- 전역 지침·응답 양식·플러그인 md 글자: 그 주 끝에 커밋되어 있던 글자 수. 응답 양식은 전역 지침을 뺀 나머지 규칙 파일의 합이다.",
    "- 자가 발전 커밋: 커밋 메시지에 \"누가 정했는지: 자가 발전\"이 있고 규칙 문서를 건드린 커밋. 줄어든 커밋은 그중 글자 수가 줄어든 것.",
    "- 메모 줄: `raw/journal/`의 그 주 날짜 파일에 적힌 메모 줄 수.",
    "- `-`는 읽을 수 없었던 값이다.",
]
USAGE_HEADER = ["주", "다시 물음", "메모 없는 지적", "모은 날", "오래된 상황판 묶음", "스킬 실행", "예약 작업이 쓴 스킬", "안 불림",
                "스킬 설명 글자", "스킬 수"]
USAGE_INTRO = [
    "# 쓰임",
    "",
    "`measure.py`(자가 발전 스킬의 스크립트)가 측정값(`metrics.md`)과 함께 고쳐 쓴다. 손으로 고치지 않는다.",
    "주는 측정값 표와 같게 나눈다.",
    "",
]
USAGE_NOTES = [
    "",
    "## 세는 방법",
    "",
    "- 다시 물음, 메모 없는 지적: 새벽 작업이 모은 말(`evolve/signals/`)의 그 주 날짜 파일에서 센다. 메모 없는 지적은 종류가 지적이고 메모·기록이 없음인 줄이다.",
    "- 모은 날: 그 주에 모은 말 목록이 있는 날 수. 목록이 하나도 없는 주는 앞의 두 칸이 `-`다.",
    "- 오래된 상황판 묶음: 상황판(`wiki/board.md`)에서 고친 날짜가 그 주의 센 마지막 날보다 14일 넘게 앞선 묶음 수.",
    "- 스킬 실행: 사람과 대화한 세션에서 Skill 도구로 부른 횟수. 예약 작업 세션은 여기에 넣지 않는다.",
    "- 예약 작업이 쓴 스킬: 스킬마다 그 스킬을 쓴 예약 작업 세션 수. Skill 도구로 불렀거나 이 플러그인 스킬의 지침 파일(`SKILL.md`, `references/`)을 읽은 세션이다. 다른 스킬이 참조로 읽은 것도 들어간다.",
    "- 안 불림: 이 플러그인의 스킬 가운데 그 주에 위 두 칸 어디에도 없는 것.",
    "- 스킬 설명 글자, 스킬 수: 그 주 끝에 커밋되어 있던 플러그인 스킬들의 `SKILL.md` 머리말 description 글자 수의 합과 스킬 수. 매번 읽히는 양은 이 칸과 `metrics.md`의 전역 지침·응답 양식 글자다.",
    "- `-`는 읽을 수 없었던 값이다.",
]
STALE_DAYS = 14
SKILL_DOC_RE = re.compile(r"(?:^|/)skills/[^/]+/SKILL\.md$")
SKILL_FILE_RE = re.compile(r"/skills/([^/]+)/(?:SKILL\.md$|references/)")
SIGNAL_ROW_RE = re.compile(r"^\| \d{2}:\d{2} \| ")
BOARD_DAY_RE = re.compile(r"^- 고친 날짜:\s*(\d{4}-\d{2}-\d{2})")
WHO_RE = re.compile(r"^[ \t]*누가 정했(?:는지|나)[ \t]*:[ \t]*(자가 발전|사용자)", re.M)   # 줄이 이 말로 시작할 때만
PLUGIN_REPO_ENV = "PLUGIN_REPO_DIR"
MEMO_RE = re.compile(r"^\d{1,2}:\d{2} \| ")
REPO_LINE_RE = re.compile(r"^- (?:저장소|위치):(.*)$", re.M)
BACKTICK_RE = re.compile(r"`([^`\s]+)`")
READ_VERB_RE = re.compile(r"^\s*(?:cd\s+\S+\s*)?(?:cat|head|tail|sed|grep|egrep|fgrep|rg|awk|less|nl|bat)\b")
SEGMENT_RE = re.compile(r"&&|\|\||;|\n|\|")
KB_ENV_NAMES = ("KNOWLEDGE_BASE_DIR", "KB")
READ_KINDS = ("index", "summary", "card", "raw")


def fail(message):
    sys.stderr.write(message + "\n")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 주
# ---------------------------------------------------------------------------

def week_start(day):
    return day - datetime.timedelta(days=day.weekday())

def weeks_to_measure(today, count):
    first = week_start(today)
    return [first - datetime.timedelta(days=7 * back) for back in range(count - 1, -1, -1)]

def local_day(timestamp):
    if not isinstance(timestamp, str) or not timestamp:
        return None
    try:
        moment = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (moment.astimezone() if moment.tzinfo else moment).date()

# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------

def git(repo, *args, raw=False):
    try:
        done = subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True)
    except OSError:
        return None
    if done.returncode != 0:
        return None
    return done.stdout if raw else done.stdout.decode("utf-8", "replace")

def toplevel(folder):
    out = git(folder, "rev-parse", "--show-toplevel") if folder and pathlib.Path(folder).is_dir() else None
    return pathlib.Path(out.strip()) if out and out.strip() else None

def main_branch(repo):
    for name in ("main", "master", "HEAD"):
        if git(repo, "rev-parse", "--verify", "-q", name) is not None:
            return name
    return None

def rev_at(repo, branch, day_after):
    """day_after(그 주 다음 날) 0시 전에 branch 에 있던 마지막 커밋."""
    moment = datetime.datetime.combine(day_after, datetime.time()).astimezone().isoformat()
    out = git(repo, "rev-list", "-1", f"--before={moment}", branch)
    return out.strip() if out and out.strip() else None

def blob_texts(repo, rev, paths):
    """{경로: 글}. 그 커밋에 없는 경로는 뺀다. git cat-file --batch 한 번으로 읽는다."""
    if not paths:
        return {}
    try:
        done = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch"], capture_output=True,
                              input="".join(f"{rev}:{path}\n" for path in paths).encode("utf-8"))
    except OSError:
        return {}
    data, position, texts = done.stdout, 0, {}
    for path in paths:
        end = data.find(b"\n", position)
        if end < 0:
            break
        head = data[position:end].split()
        position = end + 1
        if len(head) == 3 and head[1] == b"blob":
            size = int(head[2])
            texts[path] = data[position:position + size].decode("utf-8", "replace")
            position += size + 1
    return texts

def blob_chars(repo, rev, paths):
    """{경로: 글자 수}. 그 커밋에 없는 경로는 뺀다."""
    return {path: len(text) for path, text in blob_texts(repo, rev, paths).items()}

def tree_paths(repo, rev):
    out = git(repo, "ls-tree", "-r", "--name-only", "-z", rev)
    return [name for name in (out or "").split("\0") if name]

def plugin_roots(paths):
    """플러그인 폴더(.claude-plugin/plugin.json 이 든 폴더)들. 저장소 맨 위가 플러그인이거나 그런 폴더가 없으면 []."""
    roots = [name[:-len(".claude-plugin/plugin.json")] for name in paths if name.endswith(".claude-plugin/plugin.json")]
    return [] if "" in roots else roots

def plugin_md_paths(paths):
    """플러그인 폴더 아래의 md. 플러그인 폴더를 가릴 수 없으면 저장소의 md 전부."""
    roots = plugin_roots(paths)
    return [name for name in paths if name.endswith(".md") and (not roots or any(name.startswith(root) for root in roots))]

def skill_doc_paths(paths):
    """플러그인 폴더 아래의 skills/<스킬>/SKILL.md. 플러그인 폴더를 가릴 수 없으면 저장소의 그런 파일 전부."""
    roots = plugin_roots(paths)
    return [name for name in paths if SKILL_DOC_RE.search(name) and (not roots or any(name.startswith(root) for root in roots))]

def description_of(text):
    """SKILL.md 머리말의 description 값. 없으면 빈 글. 여러 줄로 적은 값(`>`, `|`, 이어 쓴 줄)은 한 줄로 잇는다."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    lines = m.group(1).splitlines() if m else []
    for index, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        value = line[len("description:"):].strip()
        more = []
        for later in lines[index + 1:]:
            if later.strip() and not later[:1].isspace():
                break
            more.append(later.strip())
        if re.match(r"^[>|][+-]?\d*$", value):
            value = ""
        value = " ".join(part for part in [value] + more if part)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value
    return ""

def description_chars(texts):
    """[SKILL.md 의 글] → [description 글자 수의 합, 스킬 수]"""
    return [sum(len(description_of(text)) for text in texts), len(texts)]

def default_rule_file(path):
    return path == "CLAUDE.md" or (path.startswith("output-styles/") and path.endswith(".md"))

def evolve_commits(repo, branch, is_rule_doc, first_day, weeks):
    """{주: [커밋 수, 줄어든 커밋 수]}. 자가 발전이 규칙 문서를 건드린 커밋."""
    counts = {week: [0, 0] for week in weeks}
    since = datetime.datetime.combine(first_day, datetime.time()).astimezone().isoformat()
    out = git(repo, "log", "--no-merges", f"--since={since}", "--format=%H%x1f%aI%x1f%B%x1e", branch) or ""
    for chunk in out.split("\x1e"):
        if "\x1f" not in chunk:
            continue
        commit, when, message = chunk.strip("\n").split("\x1f", 2)
        who = WHO_RE.findall(message)   # 그런 줄이 여럿이면 마지막 줄을 쓴다
        week = week_start(local_day(when)) if local_day(when) else None
        if not who or who[-1] != "자가 발전" or week not in counts:
            continue
        changed = git(repo, "diff-tree", "-r", "--root", "--no-commit-id", "--name-status", "-M", commit) or ""
        before, after = [], []
        for line in changed.splitlines():
            cells = line.split("\t")
            if len(cells) < 2:
                continue
            kind, old, new = cells[0][:1], cells[1], cells[-1]
            if kind != "A" and is_rule_doc(old):
                before.append(old)
            if kind != "D" and is_rule_doc(new):
                after.append(new)
        if not before and not after:
            continue
        delta = sum(blob_chars(repo, commit, after).values()) - sum(blob_chars(repo, commit + "^", before).values())
        counts[week][0] += 1
        counts[week][1] += delta < 0
    return counts

# ---------------------------------------------------------------------------
# 어디서 읽나
# ---------------------------------------------------------------------------

def claude_dir():
    return pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude").expanduser()

def load_limits(given):
    path = pathlib.Path(given).expanduser() if given else (
        pathlib.Path(os.environ["RULE_CHANGE_LIMITS"]).expanduser() if os.environ.get("RULE_CHANGE_LIMITS")
        else claude_dir() / "evolve" / "limits.json")
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}

def plugin_name(plugin):
    for manifest in (plugin / ".claude-plugin" / "plugin.json", plugin / "plugin.json"):
        if manifest.is_file():
            m = re.search(r'"name"\s*:\s*"([^"]+)"', manifest.read_text(encoding="utf-8"))
            if m:
                return m.group(1)
    return plugin.name

def card_repo(kb, name):
    card = kb / "wiki" / "projects" / f"{name}.md"
    if not card.is_file():
        return None
    for m in REPO_LINE_RE.finditer(card.read_text(encoding="utf-8")):
        for token in BACKTICK_RE.findall(m.group(1)):
            if token.startswith(("~/", "/")):
                return pathlib.Path(token).expanduser()
    return None

def tracks(repo, path):
    """repo 가 그 파일을 추적하는가. 설치본은 Claude 설정 저장소 안에 있지만 추적되지 않는다."""
    try:
        rel = pathlib.Path(path).resolve().relative_to(pathlib.Path(repo).resolve())
    except ValueError:
        return False
    return git(repo, "ls-files", "--error-unmatch", "--", str(rel)) is not None

def find_plugin_repo(given, kb):
    """플러그인 저장소의 체크아웃. 인자, 환경 변수, 지식 베이스의 플러그인 카드, 이 스크립트가 든 저장소 순서로 찾는다.
    이 스크립트가 든 저장소는 그 저장소가 이 파일을 추적할 때만 쓴다. 설치본 폴더는 Claude 설정 저장소 안이라
    그냥 쓰면 설정 저장소가 플러그인 저장소로 잡힌다. 못 찾으면 None."""
    here = pathlib.Path(__file__).resolve()
    if given:
        return toplevel(pathlib.Path(given).expanduser())
    if os.environ.get(PLUGIN_REPO_ENV):
        return toplevel(pathlib.Path(os.environ[PLUGIN_REPO_ENV]).expanduser())
    found = toplevel(card_repo(kb, plugin_name(here.parents[3])))
    if found:
        return found
    own = toplevel(here.parent)
    return own if own and tracks(own, here) else None

def installed_skill_docs():
    """이 스크립트가 든 플러그인 폴더의 SKILL.md 글들. 플러그인 폴더가 아니면 None."""
    root = pathlib.Path(__file__).resolve().parents[3]
    if not ((root / ".claude-plugin" / "plugin.json").is_file() or (root / "plugin.json").is_file()):
        return None
    texts = []
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        try:
            texts.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return texts

def installed_md_chars():
    """이 스크립트가 든 플러그인 폴더의 md 글자 수. 플러그인 저장소를 못 찾았을 때 이번 주 값으로 쓴다."""
    root = pathlib.Path(__file__).resolve().parents[3]
    if not ((root / ".claude-plugin" / "plugin.json").is_file() or (root / "plugin.json").is_file()):
        return None
    total = 0
    for path in root.rglob("*.md"):
        try:
            total += len(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return total

def load_extractor():
    """기록 스크립트(session_extract.py). 무엇이 사람이 친 글인지를 한 곳에서만 정하려고 그 판정을 빌려 쓴다."""
    path = pathlib.Path(__file__).resolve().parents[2] / "write-records" / "scripts" / "session_extract.py"
    if not path.is_file():
        fail(f"기록 스크립트를 못 찾음: {path}")
    spec = importlib.util.spec_from_file_location("session_extract", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# ---------------------------------------------------------------------------
# 세션 기록
# ---------------------------------------------------------------------------

def read_kind(rel):
    """지식 베이스 기준 경로 → index | summary | card | raw | None"""
    rel = rel.strip("\"' ").lstrip("/")
    if rel == "INDEX.md":
        return "index"
    if rel == "wiki/context.md":
        return "summary"
    if rel.startswith("wiki/projects"):
        return "card"
    if re.match(r"raw/(cases|decisions|context)(/|$)", rel):
        return "raw"
    return None

class KbPaths:
    """세션 기록에 적힌 경로가 지식 베이스의 어느 문서인지 가린다."""

    def __init__(self, roots):
        self.roots = []
        home = os.path.expanduser("~")
        for root in roots:
            root = os.path.realpath(os.path.expanduser(str(root)))
            self.roots.append(root)
        prefixes = [re.escape(root) for root in self.roots]
        prefixes += [re.escape("~" + root[len(home):]) for root in self.roots if root.startswith(home + os.sep)]
        prefixes += [r"\$\{?%s\}?" % name for name in KB_ENV_NAMES]
        self.mention = re.compile("|".join(prefixes))
        self.path = re.compile(
            r"(?:(?:%s)/|(?<![\w/.-]))((?:INDEX\.md)|(?:wiki/[\w./*-]+)|(?:raw/(?:cases|decisions|context)[\w./*-]*))"
            % "|".join(prefixes))

    def inside(self, path):
        if not isinstance(path, str) or not path:
            return None
        path = os.path.expanduser(path)
        for root in self.roots:
            if path == root:
                return ""
            if path.startswith(root + os.sep):
                return path[len(root) + 1:]
        return None

    def reads_in_tool(self, name, params, cwd):
        kinds = set()
        if name == "Read":
            rel = self.inside(params.get("file_path"))
            if rel is not None:
                kinds.add(read_kind(rel))
        elif name == "Grep":
            rel = self.inside(params.get("path"))
            if rel is not None:
                kinds.add(read_kind(rel))
        elif name == "Bash":
            command = params.get("command")
            if not isinstance(command, str):
                return kinds
            if not (self.mention.search(command) or self.inside(cwd) is not None):
                return kinds
            for segment in SEGMENT_RE.split(command):
                if not READ_VERB_RE.match(segment) or re.search(r"sed\s+-i", segment):
                    continue
                segment = re.sub(r">>?\s*\S+", " ", segment)   # 파일에 쓰는 쪽은 읽은 것이 아니다
                for m in self.path.finditer(segment):
                    kinds.add(read_kind(m.group(1)))
        kinds.discard(None)
        return kinds

def is_scheduled(data, content):
    origin = data.get("origin")
    if isinstance(origin, dict) and origin.get("subkind") == "scheduled-trigger":
        return True
    if data.get("turnOrigin") == "scheduled":
        return True
    text = content if isinstance(content, str) else " ".join(
        block.get("text") or "" for block in content or [] if isinstance(block, dict) and block.get("type") == "text")
    return text.lstrip().startswith("<scheduled-task")

def scan_file(path, session, kb_paths, extractor, main):
    """한 세션 기록 파일을 읽어 session 에 더한다. main 이 아니면(서브에이전트 기록) 도구 호출만 센다."""
    try:
        handle = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return
    with handle:
        for line in handle:
            is_user = '"type":"user"' in line or '"type": "user"' in line or "queued_command" in line
            has_tool = '"tool_use"' in line
            need_start = main and (session["start"] is None or session["cwd"] is None)
            if not (is_user and main) and not has_tool and not need_start:
                continue
            try:
                data = json.loads(line)
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue
            if main:
                if session["start"] is None and data.get("timestamp"):
                    session["start"] = data["timestamp"]
                if session["cwd"] is None and isinstance(data.get("cwd"), str):
                    session["cwd"] = data["cwd"]
            kind = data.get("type")
            if kind == "assistant":
                message = data.get("message")
                blocks = message.get("content") if isinstance(message, dict) else None
                for block in blocks if isinstance(blocks, list) else []:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    session["tools"] += 1
                    params = block.get("input") if isinstance(block.get("input"), dict) else {}
                    if block.get("name") == "Skill" and isinstance(params.get("skill"), str) and params["skill"].strip():
                        session["skills"].append((block.get("id"), data.get("timestamp"), params["skill"].strip()))
                    elif block.get("name") == "Read" and isinstance(params.get("file_path"), str):
                        read = SKILL_FILE_RE.search(params["file_path"])
                        if read:
                            session["skill_files"].add(read.group(1))
                    session["reads"] |= kb_paths.reads_in_tool(block.get("name"), params, data.get("cwd") or session["cwd"])
            elif main and kind in ("user", "attachment"):
                if kind == "user":
                    message = data.get("message")
                    if is_scheduled(data, message.get("content") if isinstance(message, dict) else None):
                        session["scheduled"] = True
                try:
                    groups = extractor.classify(data)
                except extractor.UnknownFormat:
                    continue
                if any(who == "사용자" for who, _ in groups):
                    session["messages"].append((data.get("uuid"), data.get("timestamp")))

def scan_sessions(projects, earliest, kb_paths, extractor):
    """{세션 id: {start, cwd, scheduled, tools, reads, messages, skills, skill_files}}. earliest 보다 전에 마지막으로 고친 파일은 읽지 않는다."""
    sessions = {}
    floor = datetime.datetime.combine(earliest, datetime.time()).timestamp()
    if not projects.is_dir():
        return sessions
    for folder in sorted(projects.iterdir()):
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*.jsonl")):
            try:
                if path.stat().st_mtime < floor:
                    continue
            except OSError:
                continue
            rel = path.relative_to(folder).parts
            main = len(rel) == 1
            sid = rel[0][:-len(".jsonl")] if main else rel[0]
            session = sessions.setdefault(sid, {"start": None, "cwd": None, "scheduled": False, "tools": 0,
                                                "reads": set(), "messages": [], "skills": [], "skill_files": set()})
            scan_file(path, session, kb_paths, extractor, main)
    return sessions

# ---------------------------------------------------------------------------
# 지식 베이스
# ---------------------------------------------------------------------------

def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1); fm[k.strip()] = v.split(" #")[0].strip()
    return fm

def count_cases(kb, weeks):
    counts = collections.Counter()
    for p in (kb / "raw" / "cases").glob("*.md"):
        fm = frontmatter(p.read_text(encoding="utf-8"))
        tags = [t.strip().strip("\"'") for t in fm.get("tags", "").strip("[]").split(",")]
        try:
            day = datetime.date.fromisoformat(fm.get("date", ""))
        except ValueError:
            continue
        if "notfound" not in tags and week_start(day) in weeks:
            counts[week_start(day)] += 1
    return counts

def count_memos(kb, weeks):
    counts = collections.Counter()
    for p in (kb / "raw" / "journal").glob("*.md"):
        try:
            day = datetime.date.fromisoformat(p.stem)
        except ValueError:
            continue
        if week_start(day) in weeks:
            counts[week_start(day)] += sum(1 for line in p.read_text(encoding="utf-8").splitlines() if MEMO_RE.match(line))
    return counts

def read_signal_rows(path):
    """모은 말 목록 파일의 줄. [{time, session, kind, said, have}]. 형식은 collect_signals.py 가 쓰는 표다."""
    rows = []
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if SIGNAL_ROW_RE.match(line):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) == 5:
                rows.append(dict(zip(("time", "session", "kind", "said", "have"), cells)))
    return rows

def count_signals(kb, weeks):
    """{주: [다시 물음, 메모·기록 없는 지적, 목록이 있는 날 수]}. 목록이 없는 주는 들어 있지 않다."""
    counts = {}
    for p in sorted((kb / "evolve" / "signals").glob("*.md")):
        try:
            day = datetime.date.fromisoformat(p.stem)
        except ValueError:
            continue
        if week_start(day) not in weeks:
            continue
        rows = read_signal_rows(p)
        entry = counts.setdefault(week_start(day), [0, 0, 0])
        entry[0] += sum(1 for row in rows if row["kind"] == "다시 물음")
        entry[1] += sum(1 for row in rows if row["kind"] == "지적" and row["have"] == "없음")
        entry[2] += 1
    return counts

def stale_groups(text, as_of):
    """상황판에서 고친 날짜가 as_of 보다 STALE_DAYS 일 넘게 앞선 묶음 수. 고친 날짜 줄이 없는 묶음은 세지 않는다."""
    stale, inside = 0, False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = True
            continue
        m = BOARD_DAY_RE.match(line)
        if not (inside and m):
            continue
        inside = False   # 묶음 하나에 날짜 하나만 본다
        try:
            stale += (as_of - datetime.date.fromisoformat(m.group(1))).days > STALE_DAYS
        except ValueError:
            continue
    return stale

def board_text(kb, week_is_current, day_after):
    """상황판의 글. 이번 주는 지금 파일, 지난 주는 그 주 끝에 커밋되어 있던 파일. 읽을 수 없으면 None."""
    if week_is_current:
        path = kb / "wiki" / "board.md"
        return path.read_text(encoding="utf-8") if path.is_file() else None
    branch = main_branch(kb) if toplevel(kb) else None
    rev = rev_at(kb, branch, day_after) if branch else None
    return git(kb, "show", f"{rev}:./wiki/board.md") if rev else None

def own_skills():
    """이 스크립트가 든 플러그인의 스킬 이름들(<플러그인 이름>:<스킬 폴더>). 플러그인 폴더가 아니면 []."""
    root = pathlib.Path(__file__).resolve().parents[3]
    if not ((root / ".claude-plugin" / "plugin.json").is_file() or (root / "plugin.json").is_file()):
        return []
    name = plugin_name(root)
    return sorted(f"{name}:{path.parent.name}" for path in (root / "skills").glob("*/SKILL.md"))

# ---------------------------------------------------------------------------
# 표
# ---------------------------------------------------------------------------

def show(value, suffix=""):
    return "-" if value is None else f"{value}{suffix}"

def table_row(row):
    last = datetime.date.fromisoformat(row["last_day"])
    rules = row["rule_chars"]
    guide = other = None
    if rules:
        names = list(rules)
        first = next((name for name in names if name.split("/")[-1] == "CLAUDE.md"), names[0])
        guide = rules[first]
        other = sum(size for name, size in rules.items() if name != first) if len(names) > 1 else None
    return [f"{row['week']} ~ {last.strftime('%m-%d')}", show(row["messages"]), show(row["cases"]), show(row["cases_per_100"]),
            show(row["work_sessions"]), show(row["read_index"], "%"), show(row["read_summary"], "%"),
            show(row["read_card"], "%"), show(row["read_raw"], "%"), show(guide), show(other),
            show(row["plugin_md_chars"]), show(row["evolve_commits"]), show(row["evolve_shrinking"]), show(row["memo_lines"])]

def usage_row(row):
    last = datetime.date.fromisoformat(row["last_day"])
    def counts(runs):
        ordered = sorted(runs.items(), key=lambda item: (-item[1], item[0]))
        return (", ".join(f"{name} {count}" for name, count in ordered) or "없음").replace("|", "/")
    return [f"{row['week']} ~ {last.strftime('%m-%d')}", show(row["reasks"]), show(row["bare_corrections"]),
            show(row["collected_days"]), show(row["stale_board"]), counts(row["skill_runs"]),
            counts(row["skill_runs_scheduled"]), (", ".join(row["skills_unused"]) or "없음").replace("|", "/"),
            show(row["skill_desc_chars"]), show(row["skill_count"])]

def write_rows(path, intro, header, aligns, lines_by_week, notes):
    """주마다 한 줄인 표 파일을 고쳐 쓴다. 파일에 있던 다른 주의 줄은 그대로 둔다."""
    kept = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if line.lstrip().startswith("|") and re.match(r"^\d{4}-\d{2}-\d{2}", cells[0]):
                kept[cells[0][:10]] = "| " + " | ".join(cells) + " |"
    for week, cells in lines_by_week:
        kept[week] = "| " + " | ".join(cells) + " |"
    lines = intro + ["| " + " | ".join(header) + " |", aligns]
    lines += [kept[week] for week in sorted(kept)] + notes
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def write_table(path, rows):
    write_rows(path, INTRO, HEADER, "| :- |" + " -: |" * (len(HEADER) - 1),
               [(row["week"], table_row(row)) for row in rows], NOTES)

def write_usage(path, rows):
    write_rows(path, USAGE_INTRO, USAGE_HEADER, "| :- |" + " -: |" * 4 + " :- |" * 3 + " -: |" * (len(USAGE_HEADER) - 8),
               [(row["week"], usage_row(row)) for row in rows], USAGE_NOTES)

# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("knowledge_base", nargs="?", default=os.environ.get("KNOWLEDGE_BASE_DIR"))
    ap.add_argument("--weeks", type=int, default=2)
    ap.add_argument("--today")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--projects-dir")
    ap.add_argument("--read-root", action="append", default=[])
    ap.add_argument("--min-tools", type=int, default=10)
    ap.add_argument("--rules-repo")
    ap.add_argument("--rule-files", nargs="+")
    ap.add_argument("--plugin-repo")
    ap.add_argument("--limits")
    a = ap.parse_args()
    if not a.knowledge_base:
        fail("지식 베이스를 모른다. 인자로 주거나 KNOWLEDGE_BASE_DIR 을 둔다")
    kb = pathlib.Path(a.knowledge_base).expanduser()
    if not (kb / "raw" / "journal").is_dir():
        fail(f"지식 베이스가 아님(raw/journal 없음): {kb}")
    if a.weeks < 1:
        fail("--weeks 는 1 이상")
    try:
        today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    except ValueError:
        fail(f"날짜는 YYYY-MM-DD로 적는다: {a.today}")
    weeks = weeks_to_measure(today, a.weeks)

    # 세션 기록
    extractor = load_extractor()
    roots = a.read_root or [str(kb)] + ([os.environ["KNOWLEDGE_BASE_DIR"]] if os.environ.get("KNOWLEDGE_BASE_DIR") else [])
    kb_paths = KbPaths(roots)
    projects = pathlib.Path(a.projects_dir).expanduser() if a.projects_dir else claude_dir() / "projects"
    sessions = scan_sessions(projects, weeks[0], kb_paths, extractor)
    messages, seen = collections.Counter(), set()
    work = {week: [] for week in weeks}
    skill_runs, seen_calls = {week: collections.Counter() for week in weeks}, set()
    scheduled_runs, plugin_skills = {week: collections.Counter() for week in weeks}, own_skills()
    for sid in sorted(sessions):
        session = sessions[sid]
        if session["scheduled"]:
            # 예약 작업은 지침 파일의 경로를 넘겨 스킬을 돌린다. 그 세션이 쓴 스킬마다 한 번으로 센다
            start = local_day(session["start"])
            if start and week_start(start) in scheduled_runs:
                used = {name for _, _, name in session["skills"]}
                used |= {name for name in plugin_skills if name.split(":", 1)[1] in session["skill_files"]}
                scheduled_runs[week_start(start)].update(used)
            continue
        for uuid, stamp in session["messages"]:
            key = uuid or (sid, stamp)
            day = local_day(stamp)
            if key in seen or day is None:
                continue
            seen.add(key)
            if week_start(day) in work:
                messages[week_start(day)] += 1
        for call, stamp, name in session["skills"]:
            key = call or (sid, stamp, name)
            day = local_day(stamp)
            if key in seen_calls or day is None:
                continue
            seen_calls.add(key)
            if week_start(day) in skill_runs:
                skill_runs[week_start(day)][name] += 1
        start = local_day(session["start"])
        if (start and week_start(start) in work and session["tools"] >= a.min_tools
                and kb_paths.inside(session["cwd"]) is None):
            work[week_start(start)].append(session)

    # 지식 베이스
    cases, memos = count_cases(kb, set(weeks)), count_memos(kb, set(weeks))
    signals = count_signals(kb, set(weeks))

    # 저장소
    limits = load_limits(a.limits)
    rules_repo = toplevel(pathlib.Path(a.rules_repo).expanduser() if a.rules_repo else
                          pathlib.Path(limits.get("root") or claude_dir()).expanduser())
    rule_files = [pathlib.PurePath(name).as_posix() for name in a.rule_files or list(limits.get("chars") or {})]
    rules_branch = main_branch(rules_repo) if rules_repo else None
    plugin_repo = find_plugin_repo(a.plugin_repo, kb)
    plugin_branch = main_branch(plugin_repo) if plugin_repo else None
    targets = []
    if rules_repo and rules_branch:
        names = set(rule_files)
        targets.append((rules_repo, rules_branch, (lambda path: path in names) if names else default_rule_file))
    if plugin_repo and plugin_branch and plugin_repo != rules_repo:
        roots = plugin_roots(tree_paths(plugin_repo, plugin_branch))
        targets.append((plugin_repo, plugin_branch,
                        lambda path: path.endswith(".md") and (not roots or any(path.startswith(root) for root in roots))))
    evolve = {week: None for week in weeks}
    have_rules, have_plugin = bool(rules_repo and rules_branch), bool(plugin_repo and plugin_branch)
    if not have_rules:
        sys.stderr.write("알림: 규칙 저장소를 못 찾았다(--rules-repo, 한도 파일의 root, Claude 설정 폴더 순서로 찾는다). "
                         "규칙 파일 글자 수와 자가 발전 커밋 수를 비워 둔다\n")
    if not have_plugin:
        sys.stderr.write("알림: 플러그인 저장소를 못 찾았다(--plugin-repo, $%s, 지식 베이스의 플러그인 카드, 이 스크립트가 든 저장소 "
                         "순서로 찾는다). 자가 발전 커밋 수를 비워 두고, 플러그인 md 글자 수는 이번 주만 이 스크립트가 든 "
                         "플러그인 폴더에서 센다\n" % PLUGIN_REPO_ENV)
    # 두 저장소를 다 읽었을 때만 센다. 한쪽만 센 수를 전체인 것처럼 적지 않기 위해서다
    for repo, branch, is_rule in targets if have_rules and have_plugin else []:
        for week, (total, shrinking) in evolve_commits(repo, branch, is_rule, weeks[0], weeks).items():
            evolve[week] = [(evolve[week] or [0, 0])[0] + total, (evolve[week] or [0, 0])[1] + shrinking]

    rows, usage = [], []
    for week in weeks:
        last_day = min(week + datetime.timedelta(days=6), today)
        day_after = last_day + datetime.timedelta(days=1)
        board = board_text(kb, week == weeks[-1], day_after)
        described = None
        if plugin_repo and plugin_branch:
            rev = rev_at(plugin_repo, plugin_branch, day_after)
            if rev:
                described = description_chars(list(blob_texts(plugin_repo, rev, skill_doc_paths(tree_paths(plugin_repo, rev))).values()))
        elif week == weeks[-1] and installed_skill_docs() is not None:
            described = description_chars(installed_skill_docs())
        usage.append({
            "week": week.isoformat(),
            "last_day": last_day.isoformat(),
            "reasks": signals[week][0] if week in signals else None,
            "bare_corrections": signals[week][1] if week in signals else None,
            "collected_days": signals[week][2] if week in signals else 0,
            "stale_board": stale_groups(board, last_day) if board is not None else None,
            "skill_runs": dict(skill_runs[week]),
            "skill_runs_scheduled": dict(scheduled_runs[week]),
            "skills_unused": [name for name in plugin_skills
                              if name not in skill_runs[week] and name not in scheduled_runs[week]],
            "skill_desc_chars": described[0] if described else None,
            "skill_count": described[1] if described else None,
        })
        rule_chars = plugin_chars = None
        if rules_repo and rules_branch:
            rev = rev_at(rules_repo, rules_branch, day_after)
            if rev:
                names = rule_files or [name for name in tree_paths(rules_repo, rev) if default_rule_file(name)]
                rule_chars = blob_chars(rules_repo, rev, names) or None
        if plugin_repo and plugin_branch:
            rev = rev_at(plugin_repo, plugin_branch, day_after)
            if rev:
                plugin_chars = sum(blob_chars(plugin_repo, rev, plugin_md_paths(tree_paths(plugin_repo, rev))).values())
        elif week == weeks[-1]:
            plugin_chars = installed_md_chars()
        count = len(work[week])
        share = lambda kind: round(100 * sum(1 for s in work[week] if kind in s["reads"]) / count) if count else None
        rows.append({
            "week": week.isoformat(),
            "last_day": last_day.isoformat(),
            "messages": messages[week],
            "cases": cases[week],
            "cases_per_100": round(100 * cases[week] / messages[week], 1) if messages[week] else None,
            "work_sessions": count,
            "read_index": share("index"), "read_summary": share("summary"),
            "read_card": share("card"), "read_raw": share("raw"),
            "rule_chars": rule_chars,
            "plugin_md_chars": plugin_chars,
            "evolve_commits": evolve[week][0] if evolve[week] else None,
            "evolve_shrinking": evolve[week][1] if evolve[week] else None,
            "memo_lines": memos[week],
        })
    target, usage_target = kb / "evolve" / "metrics.md", kb / "evolve" / "usage.md"
    if not a.no_write:
        write_table(target, rows)
        write_usage(usage_target, usage)
    if a.json:
        print(json.dumps({"weeks": rows, "usage": usage}, ensure_ascii=False, indent=2))
    else:
        print(("고치지 않음: " if a.no_write else "고침: ") + str(target))
        print("| " + " | ".join(HEADER) + " |")
        for row in rows:
            print("| " + " | ".join(table_row(row)) + " |")
        print(("고치지 않음: " if a.no_write else "고침: ") + str(usage_target))
        print("| " + " | ".join(USAGE_HEADER) + " |")
        for row in usage:
            print("| " + " | ".join(usage_row(row)) + " |")

if __name__ == "__main__":
    main()
