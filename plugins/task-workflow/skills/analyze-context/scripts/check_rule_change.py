#!/usr/bin/env python3
"""규칙 커밋 전 검사. 스테이징된 변경을 보고, 규칙이 늘기만 하거나 결정 기록 없이 구조를 바꾸는
커밋을 막는다. 자가 발전이 같은 절을 되풀이해 고치는 것은 막지 않고 알린다.

사용:
  check_rule_change.py [--repo <저장소>] [--who user|evolve] [--decision <id>] [--over-limit-reason <이유>]
                       [--knowledge-base <폴더>] [--limits <한도 파일>] [--today YYYY-MM-DD]
      스테이징된 변경을 검사한다. 종료 코드 0 = 통과(알림만 있어도 0), 1 = 막음.
  check_rule_change.py --audit --since <태그나 커밋> [--repo <저장소>] [--knowledge-base <폴더>] [--limits <한도 파일>]
      <since> 뒤부터 HEAD까지의 커밋을 같은 기준으로 사후에 검사한다. 토요일 점검 보고가 쓴다.
      종료 코드 0 = 어긴 커밋 없음, 1 = 있음.
  check_rule_change.py install-hook --repo <저장소> [--knowledge-base <폴더>] [--limits <한도 파일>] [--script <경로>] [--force]
      그 저장소의 git pre-commit 훅으로 이 검사를 건다.
  check_rule_change.py init-limits --repo <규칙 저장소> [--files <경로> ...] [--limits <한도 파일>]
                       [--examples <개수>] [--edits <횟수>] [--window-days <일>] [--force]
      한도 파일을 처음 만든다. 처음 값은 지금 크기다.
사용법이 틀리면 종료 코드 2다.

검사 네 가지
1. 글자 수: 한도 파일에 적힌 규칙 파일(전역 지침, 응답 양식)의 글자 수가 한도를 넘으면 막는다.
   넘는 것이 맞다고 판단했으면 이유를 --over-limit-reason(훅이면 환경 변수 RULE_CHANGE_OVER_LIMIT_REASON)으로 준다.
   이유가 있으면 막지 않고 이유와 함께 알림으로 낸다. 2번도 같다. 고치는 것이 맞는 때에도 무조건 막지는 않으려는 것이다.
   커밋 메시지에도 "한도를 넘긴 이유:"로 시작하는 줄을 적는다. 사후 검사는 그 줄을 보고 어김이 아니라 알림으로 낸다.
   이미 한도를 넘어 있는 파일을 줄이는 커밋은 알림만 낸다.
2. "예:" 개수: 규칙 문서의 절(`## ` 제목) 하나에 "예:"가 한도보다 많아지면 막는다.
   이미 한도를 넘어 있는 절은 더 늘어날 때만 막는다.
3. 같은 절 되풀이: 자가 발전이 최근 창(기본 30일) 안에 그 절을 이미 한도(기본 2번)만큼 고쳤으면 알림을 낸다. 막지 않는다.
   효과가 없던 문장을 다른 방식으로 고쳐 쓰거나 틀린 문장을 빼는 것까지 막게 되어서다. 덧대는 것은 1번과 2번이 막는다.
   줄을 지우기만 하는 변경은 세지 않는다.
   창은 검사하는 날(오늘, 또는 --today)에서 edits_window_days 일 전부터다. 전체 이력으로 세면 한두 번 고친 절이 영영 막혀서다.
   edits_since 가 있으면 창의 시작과 그 날짜 가운데 더 늦은 날부터 센다. 날짜는 커밋의 작성 날짜다.
   사후 검사는 커밋마다 그 커밋을 한 날을 기준으로 같은 창을 쓴다.
   자가 발전이 고친 커밋인지는 커밋 메시지에서 "누가 정했는지:"(예전 문구 "누가 정했나:"도 본다)로 시작하는 줄로 안다.
   줄 앞의 공백은 괜찮다. 문장 가운데에 그 말이 나오는 것은 보지 않는다. 그런 줄이 여럿이면 마지막 줄을 쓴다.
4. 구조 결정 기록: 구조를 더하거나 지우거나 옮겼는데 결정 기록 id가 없거나 그 기록이 지식 베이스 raw/decisions/ 에 없으면 막는다.
   구조 폴더에 파일을 더하거나 지우거나 옮긴 것과, 새벽 흐름과 훅 등록을 정하는 파일을 고친 것이 여기에 든다.
   구조 폴더의 있는 파일(스크립트, 훅)을 고치기만 한 것은 막지 않고 알림만 낸다. 버그를 고치는 것까지 막지 않기 위해서다.
   결정 기록의 형식은 사서 스킬 기록 규칙의 "구조 결정 기록" 절에 있다.

- 누가 정했는지는 --who 로 준다. 안 주면 환경 변수 RULE_CHANGE_WHO, 그것도 없으면 evolve(자가 발전)다.
  사용자가 정한 변경(--who user)은 1~2를 알림으로만 낸다. 3은 누가 정했든 알림이다. 4는 누가 정했든 막는다.
- 결정 기록 id는 --decision, 없으면 환경 변수 RULE_CHANGE_DECISION 이다. 사후 검사는 커밋 메시지에 적힌 D- id를 본다.
  사후 검사는 머지 커밋 메시지에 적힌 D- id도 그 머지로 들어온 커밋들(머지의 둘째 부모 쪽에서만 닿는 커밋)의 id로 친다.
  PR 하나에 결정 기록 하나를 남기고 머지 커밋(PR 제목)에 id를 적으면, 그 PR의 커밋마다 id를 적지 않아도 된다.
  그 기록이 지식 베이스에 없으면 치지 않는다.
- 지식 베이스는 --knowledge-base, 없으면 $KNOWLEDGE_BASE_DIR 이다.
- 한도 파일은 --limits, 없으면 $RULE_CHANGE_LIMITS, 없으면 <Claude 설정 폴더>/evolve/limits.json 이다
  (Claude 설정 폴더는 $CLAUDE_CONFIG_DIR 또는 ~/.claude). 한도 파일이 없으면 1은 건너뛰고 2와 3은 기본 한도로 본다.

한도 파일(JSON)
  root                  글자 수 한도가 걸린 저장소의 절대 경로. 검사하는 저장소가 이 저장소일 때만 1을 본다
  chars                 {저장소 기준 경로: 글자 수 한도}
  examples_per_section  절 하나의 "예:" 한도
  edits_per_section     자가 발전이 한 절을 고칠 수 있는 횟수
  edits_window_days     3에서 세는 기간(일). 기본 30. 검사하는 날에서 이만큼 전부터의 수정만 센다
  edits_since           (선택) YYYY-MM-DD. 있으면 3은 이 날과 창의 시작 가운데 더 늦은 날부터 센다
  created               만든 날

무엇을 규칙 문서와 구조 파일로 보나
- 규칙 문서: 한도 파일의 chars 에 적힌 파일, 지침 파일(CLAUDE.md, AGENTS.md), 스킬 문서(SKILL.md), 스킬의 references/ 아래 md,
  서브에이전트 정의(agents/*.md), 응답 양식(output-styles/*.md). assets/ 아래는 뺀다.
- 구조 폴더: 스킬 문서(skills/<스킬>/SKILL.md), 서브에이전트 정의(agents/), 훅(hooks/), 스킬의 스크립트(skills/<스킬>/scripts/).
  저장소 맨 위에 있거나 플러그인 폴더(plugins/<이름>/) 바로 아래에 있는 것만 본다. mods/ 같은 다른 폴더 안의 hooks/ 는 보지 않는다.
  저장소 맨 위의 bin/ 과 scheduled-tasks/ 도 구조 폴더다. 시험 폴더(tests/) 아래는 어디든 뺀다.
- 고치기만 해도 결정 기록이 있어야 하는 파일: skills/daily-upkeep/SKILL.md(새벽 흐름), scheduled-tasks/ 아래 지시문, hooks/hooks.json(훅 등록).
- 스킬 문서와 서브에이전트 정의의 문장을 고치는 것은 규칙 문서 수정이라 1~3으로 보고, 구조 파일 수정 알림은 내지 않는다.
"""
import argparse, collections, datetime, json, os, pathlib, re, stat, subprocess, sys

DEFAULT_EXAMPLES = 3
DEFAULT_EDITS = 2
DEFAULT_WINDOW_DAYS = 30
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WHO_ENV, DECISION_ENV, LIMITS_ENV, KB_ENV = "RULE_CHANGE_WHO", "RULE_CHANGE_DECISION", "RULE_CHANGE_LIMITS", "KNOWLEDGE_BASE_DIR"
REASON_ENV = "RULE_CHANGE_OVER_LIMIT_REASON"
REASON_LINE_RE = re.compile(r"^[ \t]*한도를 넘긴 이유:[ \t]*(\S.*)$", re.M)
REASON_GUIDE = ("넘는 것이 맞으면 이유를 --over-limit-reason(훅이면 RULE_CHANGE_OVER_LIMIT_REASON)으로 주고 "
                "커밋 메시지에 \"한도를 넘긴 이유:\" 줄을 적는다")
WHO_NAMES = {"evolve": "자가 발전", "user": "사용자"}
WHO_RE = re.compile(r"^[ \t]*누가 정했(?:는지|나)[ \t]*:[ \t]*(자가 발전|사용자)", re.M)   # 줄이 이 말로 시작할 때만
DECISION_RE = re.compile(r"\bD-\d{8}-\d{2}\b")
EXAMPLE_RE = re.compile(r"(?<![가-힣])예\s*:")
HEADING_RE = re.compile(r"^## +(.+?)\s*$")
TOP = "(첫 제목 앞)"
PLUGIN_PREFIX_RE = re.compile(r"^plugins/[^/]+/")
DECISION_GUIDE = "형식은 사서 스킬 기록 규칙의 \"구조 결정 기록\" 절"
RULE_DOC_NAMES = {"SKILL.md", "CLAUDE.md", "AGENTS.md"}   # 어느 폴더에 있든 규칙 문서인 파일 이름
HOOK_MARK = "task-workflow:check_rule_change"

def fail(message):
    """사용법이나 환경이 틀렸다. 검사 결과(0, 1)와 헷갈리지 않게 종료 코드 2로 끝낸다."""
    sys.stderr.write(message + "\n")
    sys.exit(2)

# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------

def git(repo, *args, check=False):
    done = subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    if done.returncode != 0:
        if check:
            fail(f"git {' '.join(args)} 실패: {done.stderr.strip()}")
        return None
    return done.stdout

def toplevel(folder):
    out = git(folder, "rev-parse", "--show-toplevel")
    if not out or not out.strip():
        fail(f"git 저장소가 아님: {folder}")
    return pathlib.Path(out.strip())

def show(repo, spec):
    """<커밋>:<경로> 나 :<경로>(스테이징된 내용)의 글. 없으면 None."""
    return git(repo, "show", spec)

def name_status(output):
    """git --name-status 출력 → [(상태 한 글자, 예전 경로, 새 경로)]"""
    changes = []
    for line in (output or "").splitlines():
        cells = line.split("\t")
        if len(cells) < 2:
            continue
        kind = cells[0][:1]
        changes.append((kind, cells[1], cells[-1]))
    return changes

def staged_changes(repo):
    changes = []
    for kind, old, new in name_status(git(repo, "diff", "--cached", "--name-status", "-M", check=True)):
        before = show(repo, f"HEAD:{old}") if kind != "A" else None
        after = show(repo, f":{new}") if kind != "D" else None
        changes.append((kind, old, new, before, after))
    return changes

def commit_changes(repo, commit):
    out = git(repo, "diff-tree", "-r", "--root", "--no-commit-id", "--name-status", "-M", commit, check=True)
    changes = []
    for kind, old, new in name_status(out):
        before = show(repo, f"{commit}^:{old}") if kind != "A" else None
        after = show(repo, f"{commit}:{new}") if kind != "D" else None
        changes.append((kind, old, new, before, after))
    return changes

# ---------------------------------------------------------------------------
# 한도 파일
# ---------------------------------------------------------------------------

def default_limits_path():
    if os.environ.get(LIMITS_ENV):
        return pathlib.Path(os.environ[LIMITS_ENV]).expanduser()
    claude = pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude").expanduser()
    return claude / "evolve" / "limits.json"

def load_limits(path):
    """(한도 dict, 한도 파일이 있었나)"""
    if not path.is_file():
        return {"chars": {}, "examples_per_section": DEFAULT_EXAMPLES, "edits_per_section": DEFAULT_EDITS,
                "edits_window_days": DEFAULT_WINDOW_DAYS}, False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        chars = {str(k): int(v) for k, v in (data.get("chars") or {}).items()}
        limits = {
            "root": data.get("root"),
            "chars": chars,
            "examples_per_section": int(data.get("examples_per_section", DEFAULT_EXAMPLES)),
            "edits_per_section": int(data.get("edits_per_section", DEFAULT_EDITS)),
            "edits_window_days": int(data.get("edits_window_days", DEFAULT_WINDOW_DAYS)),
            "edits_since": data.get("edits_since"),
        }
    except (ValueError, TypeError, AttributeError) as error:
        fail(f"한도 파일을 읽을 수 없음: {path} ({error})")
    if limits["edits_window_days"] < 1:
        fail(f"한도 파일의 edits_window_days 는 1 이상이어야 한다: {path}")
    if limits["edits_since"] is not None and not DAY_RE.match(str(limits["edits_since"])):
        fail(f"한도 파일의 edits_since 는 YYYY-MM-DD 다: {path}")
    return limits, True

def chars_apply(limits, repo):
    root = limits.get("root")
    return bool(root) and os.path.realpath(os.path.expanduser(root)) == os.path.realpath(repo)

# ---------------------------------------------------------------------------
# 문서를 절로 나누기
# ---------------------------------------------------------------------------

def sections(text):
    """{절 제목: 그 절의 줄들}. `## ` 제목으로 나눈다. 첫 제목 앞은 TOP 이다. 코드 블록 안의 `## `는 제목이 아니다."""
    found = collections.OrderedDict()
    name, fenced = TOP, False
    found[name] = []
    for line in (text or "").splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        m = None if fenced else HEADING_RE.match(line)
        if m:
            name = m.group(1)
            found.setdefault(name, [])
            continue
        found[name].append(line)
    return found

def added_lines(before, after):
    """after 에만 있는 줄 수(빈 줄 빼고). 0이면 지우기만 했거나 그대로다."""
    old = collections.Counter(line.strip() for line in before if line.strip())
    new = collections.Counter(line.strip() for line in after if line.strip())
    return sum((new - old).values())

def edited_sections(before, after):
    """문장이 더해지거나 바뀐 절의 제목들. 줄을 지우기만 한 절은 넣지 않는다."""
    old, new = sections(before), sections(after)
    return [name for name, lines in new.items() if added_lines(old.get(name, []), lines)]

def example_counts(text):
    return {name: len(EXAMPLE_RE.findall("\n".join(lines))) for name, lines in sections(text).items()}

# ---------------------------------------------------------------------------
# 어떤 파일인가
# ---------------------------------------------------------------------------

def is_rule_doc(path, limits, repo):
    parts = pathlib.PurePosixPath(path).parts
    if chars_apply(limits, repo) and path in limits["chars"]:
        return True
    if not path.endswith(".md") or "assets" in parts:
        return False
    if parts[-1] in RULE_DOC_NAMES:
        return True
    if "skills" in parts and "references" in parts:
        return True
    return len(parts) >= 2 and parts[-2] in ("agents", "output-styles")

def structure_place(path):
    """구조 폴더 안의 파일이면 플러그인 접두(plugins/<이름>/)를 뗀 경로, 아니면 None."""
    parts = pathlib.PurePosixPath(path).parts
    if "tests" in parts or "__pycache__" in parts:
        return None
    prefix = PLUGIN_PREFIX_RE.match(path)
    rel = path[prefix.end():] if prefix else path
    cut = pathlib.PurePosixPath(rel).parts
    if len(cut) == 3 and cut[0] == "skills" and cut[2] == "SKILL.md":
        return rel
    if len(cut) >= 4 and cut[0] == "skills" and cut[2] == "scripts":
        return rel
    if len(cut) >= 2 and cut[0] in ("agents", "hooks"):
        return rel
    if not prefix and len(cut) >= 2 and cut[0] in ("bin", "scheduled-tasks"):
        return rel
    return None

def is_flow_file(place):
    """고치기만 해도 결정 기록이 있어야 하는 파일. 새벽 흐름과 훅 등록을 정한다."""
    return place in ("skills/daily-upkeep/SKILL.md", "hooks/hooks.json") or place.startswith("scheduled-tasks/")

def structure_change(kind, old, new):
    """"block"(결정 기록이 있어야 한다) | "notice"(있는 구조 파일을 고치기만 했다) | None(구조와 상관없다)"""
    places = [place for place in (structure_place(path) for path in {old, new}) if place]
    if not places:
        return None
    if kind != "M" or any(is_flow_file(place) for place in places):
        return "block"
    # 스킬 문서와 서브에이전트 정의의 문장 수정은 규칙 문서 수정이다. 1~3이 본다
    return None if new.endswith(".md") else "notice"

# ---------------------------------------------------------------------------
# 검사
# ---------------------------------------------------------------------------

def window_start(limits, day):
    """3번 검사가 세기 시작하는 날(YYYY-MM-DD). day(검사하는 날)에서 창만큼 전과 edits_since 가운데 더 늦은 날."""
    start = (datetime.date.fromisoformat(day) - datetime.timedelta(days=limits["edits_window_days"])).isoformat()
    return max(start, str(limits["edits_since"])) if limits.get("edits_since") else start

def self_evolve_edits(repo, path, section, before_rev, start):
    """before_rev 까지의 이력에서 start 날부터 자가 발전이 path 의 그 절에 문장을 더하거나 바꾼 커밋들(짧은 해시)."""
    out = git(repo, "log", "--no-merges", "--format=%H%x1f%as%x1f%B%x1e", before_rev, "--", path)
    hits = []
    for chunk in (out or "").split("\x1e"):
        if "\x1f" not in chunk:
            continue
        commit, day, message = chunk.strip("\n").split("\x1f", 2)
        if day < start:
            continue   # 창 밖의 수정은 세지 않는다
        if who_decided(message) != "자가 발전":
            continue
        if section in edited_sections(show(repo, f"{commit}^:{path}"), show(repo, f"{commit}:{path}")):
            hits.append(commit[:7])
    return hits

def who_decided(message):
    """커밋 메시지에서 "누가 정했는지:"로 시작하는 마지막 줄의 값("자가 발전" | "사용자"). 없으면 None."""
    found = WHO_RE.findall(message)
    return found[-1] if found else None

def decision_exists(kb, rid):
    folder = kb / "raw" / "decisions"
    return any(p.name == f"{rid}.md" or p.name.startswith(rid + "-") for p in folder.glob(f"{rid}*.md"))

def examine(repo, changes, limits, who, decisions, kb, history_rev, day, reason=""):
    """(막을 것, 알림, 구조 파일) 세 목록. who 가 user 면 1~2는 알림이 된다. 3은 누가 정했든 알림이다. day 는 검사하는 날(사후 검사는 그 커밋을 한 날)."""
    blocks, notices = [], []

    def over(text):
        """한도를 넘은 것. 사용자가 정했으면 알림, 넘긴 이유가 있으면 이유와 함께 알림, 둘 다 아니면 막는다."""
        if who == "user":
            notices.append(text)
        elif reason:
            notices.append(f"{text}. 한도를 넘긴 이유가 있어 통과시킨다: {reason}")
        else:
            blocks.append(f"{text}. {REASON_GUIDE}")
    structure, modified = [], []
    for kind, old, new, before, after in changes:
        change = structure_change(kind, old, new)
        if change:
            (structure if change == "block" else modified).append(new)
        if kind == "D" or after is None or not is_rule_doc(new, limits, repo):
            continue
        # 1. 글자 수
        if chars_apply(limits, repo) and new in limits["chars"]:
            limit, size = limits["chars"][new], len(after)
            was = len(before) if before is not None else None
            if size > limit and (was is None or size > was):
                over(f"글자 수: {new} {size}자, 한도 {limit}자" + (f"(커밋 전 {was}자)" if was is not None else ""))
            elif size > limit:
                notices.append(f"글자 수: {new} {size}자로 한도 {limit}자를 넘지만 커밋 전({was}자)보다 늘지 않았다")
        # 2. 절 하나의 "예:" 개수
        cap = limits["examples_per_section"]
        had = example_counts(before) if before is not None else {}
        for name, count in example_counts(after).items():
            if count > cap and count > had.get(name, 0):
                over(f"\"예:\" 개수: {new} \"{name}\" 절 {count}개, 한도 {cap}개(커밋 전 {had.get(name, 0)}개)")
        # 3. 자가 발전이 같은 절을 되풀이해 고침
        if before is not None and history_rev:
            for name in edited_sections(before, after):
                hits = self_evolve_edits(repo, old, name, history_rev, window_start(limits, day))
                if len(hits) >= limits["edits_per_section"]:
                    notices.append(
                        f"같은 절 되풀이: {new} \"{name}\" 절을 자가 발전이 {window_start(limits, day)}부터 "
                        f"이미 {len(hits)}번 고쳤다({', '.join(hits)}). 막지 않는다. "
                        "지난번과 같은 방식으로 또 고치는 것이면 다른 방식(고쳐 쓰기, 빼기, 옮기기, 훅, 스크립트)을 따진다")
    # 4. 구조를 더하거나 지우거나 옮겼으면 결정 기록
    known = kb is not None and any(decision_exists(kb, rid) for rid in decisions)
    if structure:
        listed = structure[0] + (f" 등 {len(structure)}개" if len(structure) > 1 else "")
        if not decisions:
            blocks.append(f"구조 결정 기록: 구조를 바꿨는데({listed}) 결정 기록 id가 없다. {DECISION_GUIDE}")
        elif kb is None:
            blocks.append(f"구조 결정 기록: 지식 베이스를 몰라 결정 기록({', '.join(decisions)})이 있는지 볼 수 없다"
                          f"(구조 파일 {listed}). {DECISION_GUIDE}")
        elif not known:
            blocks.append(f"구조 결정 기록: 결정 기록 {', '.join(decisions)}이 지식 베이스 raw/decisions/ 에 없다"
                          f"(구조 파일 {listed}). {DECISION_GUIDE}")
    if modified and not known:
        listed = modified[0] + (f" 등 {len(modified)}개" if len(modified) > 1 else "")
        notices.append(f"구조 파일 수정: 있는 구조 파일을 고치기만 했다({listed}). 결정 기록 없이 통과시킨다")
    return blocks, notices, structure + modified

def knowledge_base(given):
    value = given or os.environ.get(KB_ENV)
    if not value:
        return None
    kb = pathlib.Path(value).expanduser()
    return kb if (kb / "raw" / "decisions").is_dir() else None

def head_exists(repo):
    return git(repo, "rev-parse", "--verify", "-q", "HEAD") is not None

def cmd_check(a):
    repo = toplevel(a.repo or ".")
    limits, has_limits = load_limits(pathlib.Path(a.limits).expanduser() if a.limits else default_limits_path())
    who = a.who or os.environ.get(WHO_ENV) or "evolve"
    if who not in WHO_NAMES:
        fail(f"누가 정했는지는 user 나 evolve 다: {who}")
    given = a.decision or os.environ.get(DECISION_ENV) or ""
    decisions = DECISION_RE.findall(given)
    changes = staged_changes(repo)
    today = a.today or datetime.date.today().isoformat()
    if not DAY_RE.match(today):
        fail(f"날짜는 YYYY-MM-DD로 적는다: {today}")
    reason = (a.over_limit_reason or os.environ.get(REASON_ENV) or "").strip()
    blocks, notices, structure = examine(repo, changes, limits, who, decisions, knowledge_base(a.knowledge_base),
                                         "HEAD" if head_exists(repo) else None, today, reason)
    if given and not decisions:
        notices.append(f"결정 기록 id 모양(D-YYYYMMDD-NN)이 아님: {given}")
    rule_docs = [c for c in changes if c[0] != "D" and is_rule_doc(c[2], limits, repo)]
    if not has_limits and rule_docs:
        notices.append("한도 파일이 없어 글자 수 검사는 건너뛰고 \"예:\"와 되풀이 한도는 기본값으로 봤다(init-limits 로 만든다)")
    print(f"규칙 커밋 전 검사: {repo} · 스테이징된 파일 {len(changes)}개(규칙 문서 {len(rule_docs)}, 구조 파일 {len(structure)})"
          f" · 정한 쪽: {WHO_NAMES[who]}")
    for x in notices: print("  [알림]", x)
    for x in blocks: print("  [막음]", x)
    print("  통과" if not blocks else f"  막음 {len(blocks)}건")
    return 0 if not blocks else 1

def merge_decisions(repo, since, kb):
    """{커밋: 그 커밋을 들여온 머지 커밋에 적힌 결정 기록 id들}, [(머지 해시, id들, 들어온 커밋 수)].
    머지 커밋 메시지에 지식 베이스에 있는 D- id가 있을 때만, 그 머지의 첫째 부모에서는 닿지 않고
    둘째(와 그 뒤) 부모에서 닿는 커밋들에 그 id를 준다. 지식 베이스를 모르면 아무것도 주지 않는다."""
    covered, applied = {}, []
    if kb is None:
        return covered, applied
    out = git(repo, "log", "--merges", "--format=%H%x1f%P%x1f%B%x1e", f"{since}..HEAD") or ""
    for chunk in out.split("\x1e"):
        if "\x1f" not in chunk:
            continue
        merge, parents, message = chunk.strip("\n").split("\x1f", 2)
        parents = parents.split()
        ids = [rid for rid in dict.fromkeys(DECISION_RE.findall(message)) if decision_exists(kb, rid)]
        if len(parents) < 2 or not ids:
            continue
        brought = (git(repo, "rev-list", "--no-merges", f"^{parents[0]}", *parents[1:]) or "").split()
        for commit in brought:
            covered.setdefault(commit, [])
            covered[commit] += [rid for rid in ids if rid not in covered[commit]]
        applied.append((merge[:7], ids, len(brought)))
    return covered, applied

def cmd_audit(a):
    if not a.since:
        fail("--audit 에는 --since <태그나 커밋> 이 있어야 한다")
    repo = toplevel(a.repo or ".")
    limits, _ = load_limits(pathlib.Path(a.limits).expanduser() if a.limits else default_limits_path())
    kb = knowledge_base(a.knowledge_base)
    out = git(repo, "log", "--no-merges", "--reverse", "--format=%H%x1f%as%x1f%B%x1e", f"{a.since}..HEAD")
    if out is None:
        fail(f"커밋 범위를 읽을 수 없음: {a.since}..HEAD")
    commits = [chunk.strip("\n").split("\x1f", 2) for chunk in out.split("\x1e") if "\x1f" in chunk]
    print(f"규칙 커밋 사후 검사: {repo} · {a.since}..HEAD 커밋 {len(commits)}개")
    covered, applied = merge_decisions(repo, a.since, kb)
    for merge, ids, count in reversed(applied):
        print(f"머지 {merge}의 결정 기록 {', '.join(ids)}을 그 머지로 들어온 커밋 {count}개의 결정 기록으로 쳤다")
    broken = found = noted = unmarked = looked = 0
    for commit, day, message in commits:
        changes = commit_changes(repo, commit)
        touched = [c for c in changes if structure_change(c[0], c[1], c[2])
                   or (c[0] != "D" and is_rule_doc(c[2], limits, repo))]
        if not touched:
            continue
        looked += 1
        m = who_decided(message)
        who = "user" if m == "사용자" else "evolve"
        has_parent = git(repo, "rev-parse", "--verify", "-q", f"{commit}^") is not None
        decisions = DECISION_RE.findall(message) + covered.get(commit, [])
        said = REASON_LINE_RE.findall(message)
        blocks, notices, _ = examine(repo, changes, limits, who, decisions, kb,
                                     f"{commit}^" if has_parent else None, day, said[-1].strip() if said else "")
        if not m:
            unmarked += 1
            notices.append("커밋 메시지에 누가 정했는지가 없다. 자가 발전의 변경으로 보고 검사했다")
        if not blocks and not notices:
            continue
        print(f"{commit[:7]} {day} {WHO_NAMES[who] if m else '표시 없음'} | {message.splitlines()[0]}")
        for x in blocks: print("  [어김]", x)
        for x in notices: print("  [알림]", x)
        broken += bool(blocks); found += len(blocks); noted += len(notices)
    print(f"요약: 규칙 문서나 구조 파일을 건드린 커밋 {looked}개, 어긴 커밋 {broken}개(어김 {found}건), 알림 {noted}건, "
          f"누가 정했는지 없는 커밋 {unmarked}개")
    return 0 if not broken else 1

# ---------------------------------------------------------------------------
# install-hook, init-limits
# ---------------------------------------------------------------------------

def shell_quote(value):
    return "'" + str(value).replace("'", "'\\''") + "'"

def cmd_install_hook(a):
    repo = toplevel(a.repo)
    hooks = pathlib.Path(git(repo, "rev-parse", "--git-path", "hooks", check=True).strip())
    if not hooks.is_absolute():
        hooks = repo / hooks
    target = hooks / "pre-commit"
    script = pathlib.Path(a.script).expanduser().resolve() if a.script else pathlib.Path(__file__).resolve()
    if not script.is_file():
        fail(f"검사 스크립트가 없음: {script}")
    if target.exists() and HOOK_MARK not in target.read_text(encoding="utf-8", errors="replace"):
        if not a.force:
            fail(f"다른 pre-commit 훅이 이미 있다: {target}\n덮어쓰려면 --force (있던 훅은 pre-commit.before-rule-check 로 남긴다)")
        target.replace(hooks / "pre-commit.before-rule-check")
    lines = [
        "#!/bin/sh",
        f"# {HOOK_MARK} 가 건 규칙 커밋 전 검사. `check_rule_change.py install-hook`으로 다시 만든다. 손으로 고치지 않는다.",
        "# 누가 정했는지와 구조 결정 기록 id는 환경 변수로 준다:",
        "#   RULE_CHANGE_WHO=user RULE_CHANGE_DECISION=D-YYYYMMDD-NN git commit ...",
        "# 한도를 넘겨야 하면 이유를 준다: RULE_CHANGE_OVER_LIMIT_REASON='...' git commit ...",
        f'SCRIPT="${{RULE_CHANGE_SCRIPT:-{script}}}"',
        'if [ ! -f "$SCRIPT" ]; then',
        '  echo "규칙 커밋 전 검사 스크립트가 없어 검사하지 못했다: $SCRIPT (install-hook 으로 다시 건다)" >&2',
        "  exit 0",
        "fi",
    ]
    if a.knowledge_base:
        kb = pathlib.Path(a.knowledge_base).expanduser().resolve()
        lines.append(f'[ -n "${KB_ENV}" ] || export {KB_ENV}={shell_quote(kb)}')
    if a.limits:
        limits = pathlib.Path(a.limits).expanduser().resolve()
        lines.append(f'[ -n "${LIMITS_ENV}" ] || export {LIMITS_ENV}={shell_quote(limits)}')
    lines.append('exec python3 "$SCRIPT" --repo "$(git rev-parse --show-toplevel)"')
    hooks.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"pre-commit 훅을 걸었다: {target}")
    print(f"  검사 스크립트: {script}")
    return 0

def cmd_init_limits(a):
    repo = toplevel(a.repo)
    path = pathlib.Path(a.limits).expanduser() if a.limits else default_limits_path()
    if path.exists() and not a.force:
        fail(f"한도 파일이 이미 있다: {path}\n다시 만들려면 --force")
    files = list(a.files or [])
    if not files:
        files = [name for name in ["CLAUDE.md"] + sorted(str(p.relative_to(repo)) for p in (repo / "output-styles").glob("*.md"))
                 if (repo / name).is_file()]
    if not files:
        fail("글자 수 한도를 걸 파일이 없다. --files 로 준다")
    chars, most = {}, 0
    for name in files:
        target = repo / name
        if not target.is_file():
            fail(f"파일이 없음: {target}")
        text = target.read_text(encoding="utf-8")
        chars[pathlib.PurePath(name).as_posix()] = len(text)
        most = max([most] + list(example_counts(text).values()))
    data = {
        "root": str(repo),
        "created": datetime.date.today().isoformat(),
        "chars": chars,
        "examples_per_section": a.examples if a.examples is not None else max(most, 1),
        "edits_per_section": a.edits if a.edits is not None else DEFAULT_EDITS,
        "edits_window_days": a.window_days if a.window_days is not None else DEFAULT_WINDOW_DAYS,
    }
    if data["edits_window_days"] < 1:
        fail("--window-days 는 1 이상")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"한도 파일을 만들었다: {path}")
    for name, size in chars.items():
        print(f"  글자 수 한도 {name}: {size}자")
    print(f"  절 하나의 \"예:\" 한도: {data['examples_per_section']}개, "
          f"자가 발전이 한 절을 고칠 수 있는 횟수: 최근 {data['edits_window_days']}일에 {data['edits_per_section']}번")
    return 0

# ---------------------------------------------------------------------------

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["install-hook"]:
        ap = argparse.ArgumentParser(prog="check_rule_change.py install-hook")
        ap.add_argument("--repo", required=True)
        ap.add_argument("--knowledge-base")
        ap.add_argument("--limits")
        ap.add_argument("--script", help="훅이 부를 검사 스크립트 (기본: 이 파일)")
        ap.add_argument("--force", action="store_true")
        return cmd_install_hook(ap.parse_args(argv[1:]))
    if argv[:1] == ["init-limits"]:
        ap = argparse.ArgumentParser(prog="check_rule_change.py init-limits")
        ap.add_argument("--repo", required=True)
        ap.add_argument("--files", nargs="+")
        ap.add_argument("--limits")
        ap.add_argument("--examples", type=int)
        ap.add_argument("--edits", type=int)
        ap.add_argument("--window-days", type=int)
        ap.add_argument("--force", action="store_true")
        return cmd_init_limits(ap.parse_args(argv[1:]))
    ap = argparse.ArgumentParser(prog="check_rule_change.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo")
    ap.add_argument("--who", choices=sorted(WHO_NAMES))
    ap.add_argument("--decision")
    ap.add_argument("--over-limit-reason", help="글자 수나 \"예:\" 한도를 넘겨야 하는 이유. 주면 막지 않고 알림으로 낸다")
    ap.add_argument("--knowledge-base")
    ap.add_argument("--limits")
    ap.add_argument("--today", help="검사하는 날 YYYY-MM-DD (기본 오늘). 3번 검사의 창을 여기서부터 거꾸로 센다")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--since")
    a = ap.parse_args(argv)
    return cmd_audit(a) if a.audit else cmd_check(a)

if __name__ == "__main__":
    sys.exit(main())
