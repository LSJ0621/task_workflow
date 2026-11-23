#!/usr/bin/env python3
"""세션이 시작된 폴더가 어느 프로젝트의 저장소면 그 프로젝트의 카드와 상황판 묶음을 대화에 넣는다.

SessionStart 훅이다. 표준 입력으로 받은 JSON의 cwd(세션이 시작된 폴더)를 지식 베이스의
프로젝트 카드(wiki/projects/*.md)에 적힌 저장소 위치와 대어 본다. 맞는 카드가 있으면
그 카드와 상황판(wiki/board.md)에서 그 프로젝트의 묶음만 표준 출력에 쓴다.
Claude Code는 SessionStart 훅이 종료 코드 0으로 낸 글자 출력을 대화의 맨 앞에 맥락으로 넣는다.
(공식 문서 hooks 쪽, 2026-11-23에 봄: 입력은 cwd·source가 든 JSON, 출력은 1만 자까지.)

맞는 프로젝트가 없거나, 지식 베이스 위치($KNOWLEDGE_BASE_DIR)를 모르거나, 어떤 오류가 나면
아무것도 쓰지 않고 0으로 끝낸다. 세션을 막지 않는다.

- 입력의 source가 resume이나 fork면 쓰지 않는다. 처음 시작할 때 넣은 글이 그 대화에 이미 있어서다.
  startup, clear, compact에는 쓴다(clear와 compact 뒤에는 앞에서 넣은 글이 대화에 남지 않는다).
- 저장소 위치는 카드의 "- 저장소:"(또는 "- 위치:") 줄에 백틱으로 적힌 경로 가운데 ~/ 나 / 로 시작하는 것이다.
  세션 폴더가 그 경로이거나 그 아래면 맞는 것으로 본다. 여러 카드가 맞으면 경로가 가장 긴 카드를 고른다.
  세션 폴더가 git 워크트리면 원래 저장소의 경로로도 대어 본다.
- 출력이 길면 자르고 어느 파일에서 이어 읽는지 적는다. 상황판은 긴 줄부터 줄 단위로 자른다.

규칙은 여기에 두지 않는다. 지식 베이스를 어떻게 읽는지는 전역 지침과 지식 베이스의 INDEX.md에 있다.
"""
import json
import os
import re
import sys

KB_ENV = "KNOWLEDGE_BASE_DIR"
SKIP_SOURCES = {"resume", "fork"}
REPO_LINE = re.compile(r"^- (?:저장소|위치):(.*)$", re.M)
BACKTICK = re.compile(r"`([^`\s]+)`")
MAX_CARD = 4000    # 카드에서 싣는 글자 수
MAX_BOARD = 3500   # 상황판 묶음에서 싣는 글자 수. 둘을 합쳐도 훅 출력 한도(1만 자) 안이다
MAX_BOARD_LINE = 600   # 상황판 한 줄에서 싣는 글자 수. 긴 줄 하나가 뒤의 줄(다음 할 일, 막힌 것)을 밀어내지 않게 한다


def real(path):
    return os.path.realpath(os.path.expanduser(path))


def is_inside(folder, root):
    return folder == root or folder.startswith(root.rstrip(os.sep) + os.sep)


def worktree_origin(folder):
    """folder가 git 워크트리 안이면 원래 저장소의 경로. 아니면 None. git을 부르지 않고 .git 파일만 읽는다."""
    while True:
        marker = os.path.join(folder, ".git")
        if os.path.isfile(marker):
            with open(marker, encoding="utf-8") as handle:
                first = handle.readline().strip()
            if first.startswith("gitdir:") and "/.git/worktrees/" in first:
                return real(first[len("gitdir:"):].strip().split("/.git/worktrees/")[0])
            return None
        if os.path.isdir(marker):
            return None
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent


def card_repos(text):
    for match in REPO_LINE.finditer(text):
        for token in BACKTICK.findall(match.group(1)):
            if token.startswith(("~/", "/")):
                yield real(token)


def find_card(kb, folders):
    """(카드 이름, 카드 글). 맞는 카드가 없으면 None."""
    cards = os.path.join(kb, "wiki", "projects")
    best = None
    for name in sorted(os.listdir(cards)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(cards, name), encoding="utf-8") as handle:
            text = handle.read()
        for repo in card_repos(text):
            if any(is_inside(folder, repo) for folder in folders):
                if best is None or len(repo) > best[0]:
                    best = (len(repo), name[:-len(".md")], text)
    return best[1:] if best else None


def board_block(kb, name):
    path = os.path.join(kb, "wiki", "board.md")
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    block = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            inside = line[3:].strip() == name
        if inside:
            block.append(line)
    return "\n".join(block).strip()


def clip_lines(text, limit, where):
    lines = []
    for line in text.split("\n"):
        if len(line) > limit:
            line = line[:limit].rstrip() + " (…길어서 잘랐다. 이 줄의 뒤는 %s 에서 읽는다)" % where
        lines.append(line)
    return "\n".join(lines)


def clip(text, limit, where):
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n(…길어서 잘랐다. 뒤는 %s 에서 읽는다)" % where


def build(kb, folder):
    folders = [folder]
    origin = worktree_origin(folder)
    if origin:
        folders.append(origin)
    found = find_card(kb, folders)
    if not found:
        return ""
    name, card = found
    card_path = "wiki/projects/%s.md" % name
    parts = [
        "이 세션이 시작된 폴더는 프로젝트 `%s`의 저장소다. 아래는 지식 베이스(%s)에 있는 이 프로젝트의 카드와 상황판 묶음이다. "
        "줄 끝 괄호의 id는 원본 기록(raw/)을 가리킨다. 필요할 때 그 기록만 연다." % (name, kb),
        "",
        "[프로젝트 카드: %s]" % card_path,
        clip(card.strip(), MAX_CARD, card_path),
    ]
    block = board_block(kb, name)
    if block:
        parts += ["", "[상황판: wiki/board.md 의 %s 묶음]" % name, clip(clip_lines(block, MAX_BOARD_LINE, "wiki/board.md"), MAX_BOARD, "wiki/board.md")]
    return "\n".join(parts) + "\n"


def main():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict) or data.get("source") in SKIP_SOURCES:
            return 0
        kb = os.environ.get(KB_ENV)
        folder = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR")
        if not kb or not isinstance(folder, str) or not folder:
            return 0
        kb = real(kb)
        if not os.path.isdir(os.path.join(kb, "wiki", "projects")):
            return 0
        sys.stdout.write(build(kb, real(folder)))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
