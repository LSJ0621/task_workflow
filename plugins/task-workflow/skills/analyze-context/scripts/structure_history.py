#!/usr/bin/env python3
"""구조(스킬, 서브에이전트, 훅, 스크립트, 새벽 작업의 단계)가 왜 생기고 어떻게 바뀌어 왔는지를 날짜순으로 찍는다.

사용: structure_history.py <이름> [--knowledge-base <폴더>] [--repo <저장소> ...] [--limit <줄 수>]
예:   structure_history.py write-records
      structure_history.py "기록 확인"

이름 하나로 두 가지를 모아 날짜순(오래된 것부터)으로 한 줄씩 찍는다. 칸은 ` | `로 나뉜다.
- 결정 기록: 지식 베이스 raw/decisions/ 에서 제목·태그·본문에 그 이름이 나오는 결정.
  `날짜 | 구조 결정 | id (status) | 제목 | 요지 첫 줄`. tags에 structure가 없는 결정은 둘째 칸이 `결정`이다.
  세션에서 뽑은 대화(표시 사이)에만 이름이 나오는 결정은 넣지 않는다.
- 커밋: 저장소마다 경로에 그 이름이 든 파일을 건드린 커밋과, 커밋 메시지에 그 이름이 나오는 커밋.
  `날짜 | 커밋 | <저장소 이름> <짧은 해시> | 커밋 제목 | 건드린 경로 요약`. 지운 경로의 이력도 나온다.
맨 위에는 그 이름이 든 경로가 지금 있는지를 저장소마다 한 줄씩 찍는다.
아무것도 못 찾으면 그렇다고 한 줄 찍는다. 종료 코드는 찾았든 못 찾았든 0이고, 사용법이 틀리면 1이다.

사용자가 어떤 구조의 이유와 이력을 물을 때 쓴다. 이 출력에 나온 결정 기록을 열어 이유를 읽고 답한다.

- 지식 베이스: --knowledge-base, 없으면 $KNOWLEDGE_BASE_DIR. 없으면 커밋만 찍는다.
- 저장소: --repo 를 여러 번 줄 수 있다. 안 주면 플러그인 저장소와 Claude 설정 저장소($CLAUDE_CONFIG_DIR 또는 ~/.claude)다.
  플러그인 저장소는 이 스크립트가 든 git 저장소이고, 설치본처럼 git 저장소가 아니면
  지식 베이스의 플러그인 카드(wiki/projects/<플러그인 이름>.md)에 적힌 저장소 위치를 쓴다.
- --limit: 찍는 줄 수의 한도(기본 200). 넘으면 최근 것만 찍고 몇 줄을 뺐는지 알린다.
"""
import argparse, os, pathlib, re, subprocess, sys

EXTRACT_RE = re.compile(r"<!-- extract:start -->.*?<!-- extract:end -->", re.S)
REPO_LINE_RE = re.compile(r"^- (?:저장소|위치):(.*)$", re.M)
BACKTICK_RE = re.compile(r"`([^`\s]+)`")
SUMMARY_HEADS = ("## 요지", "## 결정")
FIELD = "\x1f"

def git(repo, *args):
    try:
        done = subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True, text=True)
    except OSError:
        return None
    return done.stdout if done.returncode == 0 else None

def toplevel(folder):
    out = git(folder, "rev-parse", "--show-toplevel")
    return pathlib.Path(out.strip()) if out and out.strip() else None

def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1); fm[k.strip()] = v.split(" #")[0].strip()
    return fm

def first_line_under(text, head):
    lines = text.splitlines()
    for position, line in enumerate(lines):
        if line.strip() != head:
            continue
        for body in lines[position + 1:]:
            if re.match(r"^#{1,2} ", body):
                break
            if body.strip() and not body.startswith("#") and not body.startswith("<!--"):
                return body.strip()
    return None

def one_cell(value):
    return " ".join(str(value).replace("|", "/").split())

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

def default_repos(kb):
    repos = []
    here = pathlib.Path(__file__).resolve()
    plugin_repo = toplevel(here.parent)
    if plugin_repo is None and kb is not None:
        found = card_repo(kb, plugin_name(here.parents[3]))
        plugin_repo = toplevel(found) if found and found.is_dir() else None
    if plugin_repo:
        repos.append(plugin_repo)
    claude = pathlib.Path(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude").expanduser()
    if claude.is_dir():
        top = toplevel(claude)
        if top and top not in repos:
            repos.append(top)
    return repos

def decision_rows(kb, name):
    rows = []
    needle = name.lower()
    for p in sorted((kb / "raw" / "decisions").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        if needle not in EXTRACT_RE.sub("", text).lower():
            continue
        fm = frontmatter(text)
        if not fm.get("id"):
            continue
        tags = [t.strip() for t in fm.get("tags", "").strip("[]").split(",")]
        summary = next((line for line in (first_line_under(text, head) for head in SUMMARY_HEADS) if line), "-")
        rows.append((fm.get("date", "----------"), 0, fm["id"], "구조 결정" if "structure" in tags else "결정",
                     f"{fm['id']} ({fm.get('status', '-')})", fm.get("title", "-").strip("\"'"), summary))
    return rows

def path_specs(name):
    return [f":(glob,icase)**/*{name}*", f":(glob,icase)**/*{name}*/**"]

def commit_rows(repo, name):
    label = repo.name
    found = {}   # 해시 → [날짜, 시각(초), 제목, 건드린 경로들]
    fmt = f"--format=%x1e%H{FIELD}%as{FIELD}%at{FIELD}%s"
    by_path = git(repo, "log", "--no-merges", fmt, "--name-status", "--", *path_specs(name)) or ""
    for chunk in by_path.split("\x1e")[1:]:
        head, _, rest = chunk.partition("\n")
        commit, day, stamp, subject = head.split(FIELD, 3)
        paths = [line.split("\t") for line in rest.splitlines() if line.strip()]
        found[commit] = [day, stamp, subject, [(cells[0][:1], cells[-1]) for cells in paths]]
    by_message = git(repo, "log", "--no-merges", fmt, "-i", "-F", f"--grep={name}") or ""
    for chunk in by_message.split("\x1e")[1:]:
        commit, day, stamp, subject = chunk.strip("\n").split(FIELD, 3)
        found.setdefault(commit, [day, stamp, subject.split("\n")[0], []])
    rows = []
    for commit, (day, stamp, subject, paths) in found.items():
        if paths:
            counts = {kind: sum(1 for k, _ in paths if k == kind) for kind in "AMDR"}
            kinds = ", ".join(f"{word} {counts[kind]}" for kind, word in
                              (("A", "더함"), ("M", "고침"), ("D", "지움"), ("R", "옮김")) if counts[kind])
            touched = f"{paths[0][1]}" + (f" 등 {len(paths)}개" if len(paths) > 1 else "") + f" ({kinds})"
        else:
            touched = "커밋 메시지에 이름이 나옴"
        rows.append((day, 1, stamp.zfill(12), "커밋", f"{label} {commit[:7]}", subject, touched))
    return rows

def current_paths(repo, name):
    out = git(repo, "ls-files", "--", *path_specs(name)) or ""
    return [line for line in out.splitlines() if line.strip()]

def main():
    ap = argparse.ArgumentParser(description="이름으로 구조 결정 기록과 그 경로의 git 이력을 날짜순으로 찍는다")
    ap.add_argument("name")
    ap.add_argument("--knowledge-base", default=os.environ.get("KNOWLEDGE_BASE_DIR"))
    ap.add_argument("--repo", action="append", default=[])
    ap.add_argument("--limit", type=int, default=200)
    a = ap.parse_args()
    name = a.name.strip()
    if not name or any(ch in name for ch in "*?[]\n"):
        sys.exit("이름이 비었거나 *, ?, [, ] 가 들어 있다")
    kb = pathlib.Path(a.knowledge_base).expanduser() if a.knowledge_base else None
    if kb is not None and not (kb / "raw" / "decisions").is_dir():
        sys.exit(f"지식 베이스가 아님(raw/decisions 없음): {kb}")
    repos = []
    for given in a.repo:
        top = toplevel(pathlib.Path(given).expanduser())
        if top is None:
            sys.exit(f"git 저장소가 아님: {given}")
        repos.append(top)
    repos = repos or default_repos(kb)

    print(f"이름: {name}")
    for repo in repos:
        paths = current_paths(repo, name)
        if paths:
            print(f"지금 있는 경로({repo.name}): {paths[0]}" + (f" 등 {len(paths)}개" if len(paths) > 1 else ""))
        else:
            print(f"지금 있는 경로({repo.name}): 없음")
    if kb is None:
        print("지식 베이스를 몰라 결정 기록은 찾지 않았다")
    rows = decision_rows(kb, name) if kb is not None else []
    for repo in repos:
        rows += commit_rows(repo, name)
    rows.sort(key=lambda row: row[:3])   # 날짜, 같은 날이면 결정 먼저, 그다음 커밋한 순서
    if not rows:
        print("이 이름이 나오는 결정 기록과 커밋을 찾지 못했다")
        return
    if len(rows) > a.limit:
        print(f"(오래된 {len(rows) - a.limit}줄은 뺐다. 전부 보려면 --limit 을 올린다)")
        rows = rows[-a.limit:]
    for day, _, _, kind, ident, title, detail in rows:
        print(" | ".join([day, kind, ident, one_cell(title), one_cell(detail)]))

if __name__ == "__main__":
    main()
