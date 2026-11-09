#!/usr/bin/env bash
# 지식 베이스 메모 자동 push 훅
#
# 목적: 사서가 낮에 남긴 메모 커밋(raw/journal/)을 하루에 몇 번만 push한다.
#       메모마다 push하면 과해서, 세션이 응답을 끝낼 때(Stop)와 세션이 닫힐 때(SessionEnd) 조건을 보고 한다.
#
# push하는 조건 세 가지. 하나라도 아니면 아무것도 안 하고 종료 코드 0.
#   1. 대상 폴더가 지식 베이스다: INDEX.md와 raw/journal/이 있는 git 저장소다.
#   2. raw/journal/을 건드린 push 안 된 커밋이 있다: 현재 브랜치에 upstream이 있고 `git log @{u}..HEAD -- raw/journal/`이 비어 있지 않다.
#   3. 마지막 push 시도가 30분 넘게 지났다: 도장 파일 .git/journal-push-stamp가 없거나 1800초 이상 전이다.
#      도장은 push를 시도할 때 갱신한다(성공·실패 무관). 실패를 매 응답마다 되풀이하지 않기 위해서다.
#
# 대상 폴더: stdin 훅 JSON의 "cwd"(없으면 $PWD)가 지식 베이스 모양이면 그 폴더.
#   아니면 $KNOWLEDGE_BASE_DIR가 설정돼 있고 그 폴더가 지식 베이스 모양일 때 그 폴더.
#   팀장·작업 점검 세션은 코드 저장소에서 열려 $KNOWLEDGE_BASE_DIR에 메모를 커밋하기 때문이다.
#   둘 다 아니면 건너뛴다.
# 네트워크를 쓰는 명령은 push와, 거부됐을 때의 pull --rebase뿐이다. fetch를 따로 하지 않는다.
#
# 시험용 환경 변수
#   JOURNAL_PUSH_INTERVAL  도장 간격(초). 기본 1800.
#   JOURNAL_PUSH_DIR       대상 폴더를 stdin 대신 강제.
#   JOURNAL_PUSH_VERBOSE   1이면 건너뛴 이유나 결과를 한 줄 찍는다. 기본은 아무것도 안 찍는다.
#
# 어떤 경우에도 종료 코드 0. 훅이 실패로 보이면 세션이 멈추기 때문이다.

trap 'exit 0' EXIT

say() {
  if [ "${JOURNAL_PUSH_VERBOSE:-0}" = "1" ]; then
    echo "push-journal: $*"
  fi
}

interval="${JOURNAL_PUSH_INTERVAL:-1800}"

# 조건 1: 지식 베이스 모양인가. 아니면 이유를 전역 변수 why에 남기고 1을 돌려준다.
why=""
is_kb() {
  local d="$1"
  if [ -z "$d" ] || [ ! -d "$d" ]; then
    why="폴더 없음 ($d)"; return 1
  fi
  if [ ! -f "$d/INDEX.md" ]; then
    why="INDEX.md 없음 ($d)"; return 1
  fi
  if [ ! -d "$d/raw/journal" ]; then
    why="raw/journal/ 없음 ($d)"; return 1
  fi
  if ! git -C "$d" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    why="git 저장소 아님 ($d)"; return 1
  fi
  return 0
}

# 대상 폴더 정하기
dir=""
if [ -n "${JOURNAL_PUSH_DIR:-}" ]; then
  # 시험용 강제. 이것만 본다.
  dir="$JOURNAL_PUSH_DIR"
  if ! is_kb "$dir"; then
    say "건너뜀: $why"
    exit 0
  fi
else
  input=""
  if [ ! -t 0 ]; then
    input="$(cat 2>/dev/null)"
  fi
  cwd="$(printf '%s' "$input" | tr -d '\n' | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
  if [ -z "$cwd" ]; then
    cwd="$PWD"
  fi
  if is_kb "$cwd"; then
    dir="$cwd"
  else
    why_cwd="$why"
    if [ -n "${KNOWLEDGE_BASE_DIR:-}" ] && is_kb "$KNOWLEDGE_BASE_DIR"; then
      dir="$KNOWLEDGE_BASE_DIR"
    else
      if [ -n "${KNOWLEDGE_BASE_DIR:-}" ]; then
        say "건너뜀: cwd는 $why_cwd. KNOWLEDGE_BASE_DIR는 $why"
      else
        say "건너뜀: $why_cwd. KNOWLEDGE_BASE_DIR 미설정"
      fi
      exit 0
    fi
  fi
fi

# 조건 2: push 안 된 raw/journal 커밋이 있는가
if ! git -C "$dir" rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  say "건너뜀: upstream 없음"
  exit 0
fi
pending="$(git -C "$dir" log '@{u}..HEAD' --oneline -- raw/journal/ 2>/dev/null)"
if [ -z "$pending" ]; then
  say "건너뜀: push 안 된 raw/journal 커밋 없음"
  exit 0
fi

# 조건 3: 마지막 push 시도가 interval초 넘게 지났는가
gitdir="$(git -C "$dir" rev-parse --git-dir 2>/dev/null)"
case "$gitdir" in
  /*) ;;
  *) gitdir="$dir/$gitdir" ;;
esac
stamp="$gitdir/journal-push-stamp"
if [ -f "$stamp" ]; then
  now="$(date +%s)"
  mtime="$(stat -f %m "$stamp" 2>/dev/null || stat -c %Y "$stamp" 2>/dev/null || echo 0)"
  age=$(( now - mtime ))
  if [ "$age" -lt "$interval" ]; then
    say "건너뜀: 마지막 push 시도 ${age}초 전 (간격 ${interval}초)"
    exit 0
  fi
fi

# push 시도. 도장은 성공·실패 무관하게 먼저 찍는다.
touch "$stamp" 2>/dev/null

if git -C "$dir" push --quiet >/dev/null 2>&1; then
  say "push 함"
  exit 0
fi

# 거부됨. 작업 트리가 깨끗할 때만 rebase 한 번 뒤 다시 push.
if [ -n "$(git -C "$dir" status --porcelain 2>/dev/null)" ]; then
  say "push 거부됨. 작업 트리가 더러워 rebase 안 함"
  exit 0
fi
if git -C "$dir" pull --rebase --quiet >/dev/null 2>&1; then
  if git -C "$dir" push --quiet >/dev/null 2>&1; then
    say "rebase 뒤 push 함"
  else
    say "rebase 뒤에도 push 실패"
  fi
else
  git -C "$dir" rebase --abort >/dev/null 2>&1
  say "pull --rebase 실패. 되돌림"
fi
exit 0
