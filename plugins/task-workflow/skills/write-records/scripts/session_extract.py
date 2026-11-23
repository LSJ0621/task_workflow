#!/usr/bin/env python3
"""세션 기록(jsonl)에서 정해진 범위를 그대로 뽑는다.

명령: find, list, extract, verify, confirm, pending
종료 코드: 0 성공, 1 사용법 오류, 2 세션이나 uuid를 못 찾음, 3 모르는 형식,
          4 비밀값 모양, 5 verify 불일치

세션 기록은 <projects-dir>/*/<세션 id>.jsonl 이다. 폴더 이름이 아니라 세션 id로 찾는다.
pending은 세션 기록을 읽지 않는다. 지식 베이스에 기록할 것이 남았는지만 센다.
파이썬 표준 라이브러리만 쓴다.

기록 형식은 둘이다.
- 새 형식: `extract --save <지식 베이스>`로 뽑는다. 발췌 전문은 <지식 베이스>/raw/sessions/<세션 id>.md 에
  범위 묶음(`<!-- range:start <첫 uuid>..<끝 uuid> -->` ~ `<!-- range:end -->`)으로 한 번만 적고,
  기록의 표시 사이에 넣을 글(발췌 위치 한 줄, 사용자 말, 도구 줄 가운데 Skill과 Read)을 표준 출력에 찍는다.
  verify는 표시 사이를 다시 뽑은 그 글과, 발췌 파일의 범위 묶음을 다시 뽑은 전문과 글자 단위로 비교한다.
- 예전 형식: 표시 사이에 발췌 전문이 통째로 있다. `--save` 없는 extract의 출력이다. verify는 예전과 똑같이 본다.
표시 사이의 첫 줄이 "발췌: "로 시작하면 새 형식이다.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NOT_FOUND = 2
EXIT_UNKNOWN = 3
EXIT_SECRET = 4
EXIT_MISMATCH = 5

DEFAULT_PROJECTS_DIR = os.path.join("~", ".claude", "projects")
MARK_START = "<!-- extract:start -->"
MARK_END = "<!-- extract:end -->"
OMITTED_TEXT = "> [비밀값이 있어 뺌]"
IMAGE_TEXT = "[이미지]"
DONE_PREFIX = "정리됨:"  # 메모 파일에서 여기까지 기록했다는 줄. 한 파일에 여러 개 있을 수 있다
RECORD_DIRS = ("cases", "decisions", "context")
SESSIONS_DIR = ("raw", "sessions")       # 세션 발췌 파일을 두는 곳. 세션마다 파일 하나
EXCERPT_PREFIX = "발췌: "                # 새 형식 기록의 표시 사이 첫 줄(발췌 위치)
RANGE_START_PREFIX = "<!-- range:start "
RANGE_END = "<!-- range:end -->"
RANGE_START_RE = re.compile(r"^<!-- range:start (\S+)\.\.(\S+?)(?: omitted:(\S+))? -->$")
DIGEST_TOOL_RE = re.compile(r"^- (?:Skill|Read)(?:: |$)")  # 기록에 남기는 도구 줄
KB_ENV = "KNOWLEDGE_BASE_DIR"

# ---------------------------------------------------------------------------
# 아는 종류 목록. 여기에 없는 종류가 범위 안에 있으면 종료 코드 3을 낸다.
# 새 종류를 더할 때는 싣는지 빼는지와 그 이유를 한 줄로 적는다.
# ---------------------------------------------------------------------------

# 줄 종류(type) 가운데 내용을 보고 싣는 것
LINE_TYPES_READ = {
    "user",        # 사용자가 친 글이 여기 있다. 도구 결과와 끼워 넣은 알림도 같은 종류로 온다(아래에서 가른다)
    "assistant",   # 에이전트가 보인 글과 도구 호출이 여기 있다
    "attachment",  # 대부분 시스템이 끼워 넣은 것이지만, 작업 중에 사용자가 친 글(queued_command)이 여기로 온다
    "system",      # 싣지 않는다. 다만 subtype을 아는지 본다
}

# 줄 종류 가운데 통째로 빼는 것. 대화가 아니라 앱이 남기는 장부다(uuid도 없다)
LINE_TYPES_SKIP = {
    "queue-operation",           # 입력 대기열 장부. 같은 글이 user 줄이나 queued_command로 다시 나온다
    "last-prompt",               # 마지막 입력의 사본. 원래 줄이 따로 있다
    "file-history-snapshot",     # 파일 되돌리기용 사본
    "file-history-delta",        # 파일 되돌리기용 변경분
    "api-request",               # API 요청 장부. 대화 줄의 사본이다
    "api-request-blob",          # API 요청에 실린 메시지 사본
    "api-request-shape",         # API 요청 모양 장부
    "atis-latch",                # 앱 내부 상태
    "agent-name",                # 세션에 붙은 이름
    "mode",                      # 세션 모드 표시
    "permission-mode",           # 권한 모드 표시
    "ai-title",                  # 앱이 지은 세션 제목
    "custom-title",              # 사용자가 붙인 세션 제목. 대화가 아니다
    "bridge-session",            # 원격 연결 장부
    "relocated",                 # 세션이 폴더를 옮긴 표시
    "frame-link",                # 화면 연결 장부
    "tools-used",                # 쓴 도구 이름 모음. 도구 호출은 assistant 줄에서 싣는다
    "session-owner",             # 계정 표시
    "artifact-autoreact-ledger", # 아티팩트 장부
    "artifact-comment-monitor",  # 아티팩트 댓글 감시 장부
    "pr-link",                   # PR 연결 표시
    "cost-state",                # 비용 집계
    "summary",                   # 예전 형식의 세션 요약 줄. 대화가 아니다
    "data-flow-records",         # 도구 목록과 도구 호출이 어디서 왔는지 적는 장부. 글이 없다. 도구 호출은 assistant 줄에서 싣는다
}

# system 줄의 subtype. 전부 싣지 않는다
SYSTEM_SUBTYPES_SKIP = {
    "stop_hook_summary",  # 훅 실행 요약
    "turn_duration",      # 한 차례에 걸린 시간
    "away_summary",       # 자리를 비운 사이 요약. 앱이 만든 글이다
    "local_command",      # 앱 안 명령의 출력
    "informational",      # 앱 알림
    "compact_boundary",   # 요약(compact)이 일어난 자리 표시
    "api_error",          # API 오류 표시
}

# attachment 줄의 종류. queued_command만 내용을 보고, 나머지는 시스템이 끼워 넣은 것이라 뺀다
ATTACHMENT_QUEUED = "queued_command"  # 작업 중에 들어온 입력. 사람이 친 것만 싣는다
ATTACHMENT_TYPES_SKIP = {
    "hook_success",              # 훅 출력
    "hook_system_message",       # 훅이 낸 알림
    "hook_additional_context",   # 훅이 끼워 넣은 글
    "async_hook_response",       # 늦게 온 훅 출력
    "output_style",              # 응답 양식 표시
    "output_style_instructions", # 응답 양식 본문
    "total_tokens_reminder",     # 토큰 사용량 알림
    "deferred_tools_record",     # 도구 목록 장부
    "deferred_tools_delta",      # 도구 목록 변경분
    "environment",               # 실행 환경 알림
    "batching_reminder_sent",    # 앱 내부 알림
    "silent_turn_reminder",      # 앱 내부 알림
    "prompt_snapshot",           # 시스템 지시문 사본
    "remote_session_change",     # 원격 세션 상태
    "edited_text_file",          # 파일이 바뀌었다는 알림
    "date",                      # 날짜 알림
    "skill_listing",             # 스킬 목록
    "skill_mention",             # 스킬 언급 표시
    "invoked_skills",            # 부른 스킬 장부. 스킬 호출은 도구 줄에서 싣는다
    "mcp_instructions_delta",    # 연결 도구 안내문
    "instructions",              # 지침 파일 본문
    "nested_memory",             # 지침 파일 본문
    "model",                     # 모델 표시
    "agent_listing_delta",       # 서브에이전트 목록
    "session_context",           # 세션 환경 알림
    "credential_org",            # 계정 표시
    "auto_mode",                 # 모드 알림
    "auto_mode_exit",            # 모드 알림
    "plan_mode",                 # 모드 알림
    "plan_mode_exit",            # 모드 알림
    "plan_mode_reentry",         # 모드 알림
    "plan_file_reference",       # 계획 파일 사본
    "language",                  # 언어 설정 알림
    "command_permissions",       # 권한 설정 알림
    "compact_file_reference",    # 요약 뒤 다시 실은 파일 표시
    "file",                      # 끼워 넣은 파일 본문
    "directory",                 # 끼워 넣은 폴더 목록
    "thinking_drop",             # 생각 과정을 버렸다는 표시
}

# user 줄의 origin.kind
USER_ORIGIN_HUMAN = "human"  # 사람이 친 글. 싣는다
USER_ORIGINS_SKIP = {
    "task-notification",  # 서브에이전트·예약 작업이 끝났다는 알림. 시스템이 만든 글이다
    "peer",               # 다른 세션이 보낸 글. 사용자가 친 것이 아니다
}

# origin이 없는 user 줄은 사람이 친 글이 아니다. 아래 모양 가운데 하나여야 하고, 아니면 모르는 형식으로 본다
# (origin 칸이 없던 예전 형식의 사용자 글을 말없이 빼지 않기 위해서다)
USER_NO_ORIGIN_TAGS_SKIP = {
    "command-name",          # 앱 안 명령(/compact 같은 것)
    "command-message",       # 앱 안 명령
    "local-command-stdout",  # 앱 안 명령의 출력
    "local-command-stderr",  # 앱 안 명령의 출력
    "local-command-caveat",  # 앱 안 명령에 붙는 알림
    "bash-input",            # 사용자가 직접 돌린 셸 명령. 명령어 본문은 싣지 않는다
    "bash-stdout",           # 그 셸 명령의 출력
    "bash-stderr",           # 그 셸 명령의 출력
    "system-reminder",       # 시스템 알림
    "task-notification",     # 작업 알림
    "scheduled-task",        # 예약 작업 지시문
}
USER_NO_ORIGIN_SOURCES_SKIP = {
    "sdk",     # 앱이나 다른 세션이 프로그램으로 넣은 지시문(예약 실행, 넘겨받은 세션의 첫 지시)
    "system",  # 시스템이 넣은 글
}
USER_NO_ORIGIN_TEXT_SKIP = "[Request interrupted"  # 사용자가 멈췄다는 표시. 앱이 만든 글이다

# 사람이 친 글 앞뒤에 시스템이 끼워 넣는 묶음. 통째로 뺀다
INJECTED_TAGS = (
    "system-reminder",        # 시스템 알림
    "artifact-view-context",  # 사용자가 보고 있던 아티팩트 정보
    "side-sessions-event",    # 다른 세션 소식
)
# 사람이 친 글 맨 앞에 올 수 있고 그대로 두는 표시
USER_TAGS_KEEP = {
    "pasted_content",  # 붙여 넣은 글의 자리 표시. 사용자가 넣은 것이라 둔다
}

# user 줄의 content 블록
USER_BLOCK_TEXT = "text"          # 글. 싣는다
USER_BLOCK_IMAGE = "image"        # 그림. 내용 대신 [이미지]로 적는다
USER_BLOCK_RESULT = "tool_result" # 도구 결과. 싣지 않는다

# assistant 줄의 content 블록
ASSISTANT_BLOCK_TEXT = "text"      # 사용자에게 보인 글. 싣는다
ASSISTANT_BLOCK_TOOL = "tool_use"  # 도구 호출. 정해진 칸만 싣는다
ASSISTANT_BLOCKS_SKIP = {
    "thinking",           # 생각 과정. 싣지 않는다
    "redacted_thinking",  # 가려진 생각 과정. 싣지 않는다
}

# 도구마다 싣는 칸. 여기 없는 도구는 이름만 싣는다
TOOL_FIELDS = {
    "Skill": ("skill",),                        # 스킬 이름
    "Read": ("file_path",),                     # 파일 경로
    "Edit": ("file_path",),                     # 파일 경로
    "Write": ("file_path",),                    # 파일 경로
    "Bash": ("description",),                   # 설명만. 명령어 본문은 싣지 않는다
    "Agent": ("subagent_type", "description"),  # 서브에이전트 종류와 설명. 지시문은 싣지 않는다
}

# 비밀값 모양. 뽑은 글에 보이면 출력하지 않는다
SECRET_PATTERNS = (
    ("sk-", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{16,}")),
    ("AKIA", re.compile(r"(?<![A-Za-z0-9])A[KS]IA[0-9A-Z]{16}")),
    ("ghp_", re.compile(r"(?<![A-Za-z0-9])(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("xox", re.compile(r"(?<![A-Za-z0-9])xox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("-----BEGIN", re.compile(r"-----BEGIN [A-Z ]+-----")),
    ("Bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}")),
    ("password=", re.compile(
        r"(?i)(?:password|passwd|pwd|secret|token|api[_\-]?key|access[_\-]?key)"
        r"[\"']?\s*[=:]\s*[\"']?[A-Za-z0-9_\-./+]{8,}")),
)


class ExtractError(Exception):
    """종료 코드를 가진 오류."""

    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code
        self.message = message


class UnknownFormat(Exception):
    def __init__(self, kind):
        Exception.__init__(self, kind)
        self.kind = kind


# ---------------------------------------------------------------------------
# 세션 기록 읽기
# ---------------------------------------------------------------------------

def projects_dir_of(args):
    return os.path.expanduser(getattr(args, "projects_dir", None) or DEFAULT_PROJECTS_DIR)


def session_files(projects_dir):
    """<projects-dir>/*/<id>.jsonl 전부. 서브에이전트 기록(더 깊은 폴더)은 보지 않는다."""
    found = []
    if not os.path.isdir(projects_dir):
        return found
    for folder in sorted(os.listdir(projects_dir)):
        path = os.path.join(projects_dir, folder)
        if not os.path.isdir(path):
            continue
        for name in sorted(os.listdir(path)):
            if name.endswith(".jsonl"):
                found.append(os.path.join(path, name))
    return found


def find_session_file(projects_dir, session_id):
    name = session_id + ".jsonl"
    matches = [p for p in session_files(projects_dir) if os.path.basename(p) == name]
    if not matches:
        raise ExtractError(EXIT_NOT_FOUND, "세션 기록을 못 찾음: %s" % session_id)
    # 같은 id가 두 폴더에 있으면 더 큰 쪽(더 많이 이어 쓴 쪽)을 쓴다. 크기가 같으면 경로 순
    matches.sort(key=lambda p: (-os.path.getsize(p), p))
    return matches[0]


def read_lines(path):
    """(줄 번호, dict 또는 None) 목록. 빈 줄은 뺀다. JSON이 아니면 None."""
    out = []
    with open(path, encoding="utf-8") as handle:
        for number, raw in enumerate(handle, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except ValueError:
                data = None
            if not isinstance(data, dict):
                data = None
            out.append((number, data))
    return out


def local_time(timestamp):
    if not isinstance(timestamp, str) or not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone()


def hhmm(timestamp):
    moment = local_time(timestamp)
    return moment.strftime("%H:%M") if moment else "--:--"


# ---------------------------------------------------------------------------
# 한 줄을 묶음으로 바꾸기
# ---------------------------------------------------------------------------

_OPEN_TAG = re.compile(r"\s*<([A-Za-z][\w\-]*)(?:\s[^>]*)?>")


def strip_injected(text):
    """글 앞뒤에 시스템이 끼워 넣은 묶음을 뺀다. 가운데 것은 건드리지 않는다."""
    while True:
        match = _OPEN_TAG.match(text)
        if not match or match.group(1) not in INJECTED_TAGS:
            break
        closing = "</%s>" % match.group(1)
        end = text.find(closing, match.end())
        if end < 0:
            break
        text = text[end + len(closing):]
    while True:
        stripped = text.rstrip()
        hit = None
        for tag in INJECTED_TAGS:
            closing = "</%s>" % tag
            if stripped.endswith(closing):
                start = stripped.rfind("<" + tag)
                if start >= 0 and _OPEN_TAG.match(stripped, start):
                    hit = start
                break
        if hit is None:
            break
        text = stripped[:hit]
    return text.strip()


def _tag_body(text, tag):
    match = re.search(r"<%s>(.*?)</%s>" % (tag, tag), text, re.S)
    return match.group(1).strip() if match else ""


def human_text(text):
    """사람이 친 글 하나를 정리한다. 끼워 넣은 것을 빼고 나머지는 그대로 둔다."""
    text = strip_injected(text.replace("\r\n", "\n"))
    if not text:
        return ""
    match = _OPEN_TAG.match(text)
    if match:
        tag = match.group(1)
        if tag in ("command-message", "command-name"):
            # 사용자가 친 슬래시 명령. 친 모양(/이름 인자)으로 되돌려 싣는다
            name = _tag_body(text, "command-name") or _tag_body(text, "command-message")
            args = _tag_body(text, "command-args")
            return (name + " " + args).strip()
        looks_injected = ("-" in tag or "_" in tag) and tag == tag.lower()
        if looks_injected and tag not in USER_TAGS_KEEP and ("</%s>" % tag) in text:
            raise UnknownFormat("user.tag:" + tag)
    return text


def human_content(content):
    """사람이 친 content(문자열 또는 블록 목록)를 글 하나로 만든다."""
    if isinstance(content, str):
        return human_text(content)
    if not isinstance(content, list):
        raise UnknownFormat("user.content:" + type(content).__name__)
    parts = []
    for block in content:
        kind = block.get("type") if isinstance(block, dict) else type(block).__name__
        if kind == USER_BLOCK_TEXT:
            text = human_text(block.get("text") or "")
            if text:
                parts.append(text)
        elif kind == USER_BLOCK_IMAGE:
            parts.append(IMAGE_TEXT)
        else:
            raise UnknownFormat("user.block:%s" % kind)
    return "\n".join(parts)


def one_line(value):
    return " ".join(str(value).split())


def tool_item(block):
    name = block.get("name")
    if not isinstance(name, str) or not name:
        raise UnknownFormat("assistant.tool_use:이름 없음")
    params = block.get("input")
    if not isinstance(params, dict):
        params = {}
    fields = TOOL_FIELDS.get(name)
    if not fields:
        return "- " + name
    values = [one_line(params.get(field) or "") for field in fields]
    if not any(values):
        return "- " + name
    return "- %s: %s" % (name, " | ".join(value or "-" for value in values))


def quote(text):
    lines = []
    for line in text.split("\n"):
        line = line.rstrip("\r")
        lines.append("> " + line if line else ">")
    return lines


def classify_user(data):
    message = data.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, list):
        kinds = set()
        for block in content:
            kind = block.get("type") if isinstance(block, dict) else type(block).__name__
            if kind not in (USER_BLOCK_TEXT, USER_BLOCK_IMAGE, USER_BLOCK_RESULT):
                raise UnknownFormat("user.block:%s" % kind)
            kinds.add(kind)
        if USER_BLOCK_RESULT in kinds:
            return []  # 도구 결과는 싣지 않는다
    elif not isinstance(content, str):
        raise UnknownFormat("user.content:" + type(content).__name__)

    if data.get("isMeta") or data.get("isCompactSummary") or data.get("isVisibleInTranscriptOnly"):
        return []  # 시스템이 넣은 글(스킬 본문, 요약, 알림)

    origin = data.get("origin")
    if isinstance(origin, dict):
        kind = origin.get("kind")
        if kind == USER_ORIGIN_HUMAN:
            text = human_content(content)
            return [("사용자", quote(text))] if text else []
        if kind in USER_ORIGINS_SKIP:
            return []
        raise UnknownFormat("user.origin:%s" % kind)
    if origin is not None:
        raise UnknownFormat("user.origin:" + type(origin).__name__)

    # origin이 없다. 아는 모양일 때만 뺀다
    if data.get("promptSource") in USER_NO_ORIGIN_SOURCES_SKIP:
        return []
    if data.get("turnOrigin") in USER_NO_ORIGIN_SOURCES_SKIP:
        return []
    texts = [content] if isinstance(content, str) else [
        block.get("text") or "" for block in content if block.get("type") == USER_BLOCK_TEXT]
    for text in texts:
        if text.lstrip().startswith(USER_NO_ORIGIN_TEXT_SKIP):
            continue
        match = _OPEN_TAG.match(text)
        if match and match.group(1) in USER_NO_ORIGIN_TAGS_SKIP:
            continue
        raise UnknownFormat("user:origin 없음")
    return []


def classify_assistant(data):
    message = data.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        content = [{"type": ASSISTANT_BLOCK_TEXT, "text": content}]
    if not isinstance(content, list):
        raise UnknownFormat("assistant.content:" + type(content).__name__)
    groups = []
    for block in content:
        kind = block.get("type") if isinstance(block, dict) else type(block).__name__
        if kind == ASSISTANT_BLOCK_TEXT:
            text = (block.get("text") or "").replace("\r\n", "\n").strip("\n")
            if text.strip():
                groups.append(("에이전트", quote(text)))
        elif kind == ASSISTANT_BLOCK_TOOL:
            item = tool_item(block)
            if groups and groups[-1][0] == "도구":
                groups[-1][1].append(item)
            else:
                groups.append(("도구", [item]))
        elif kind in ASSISTANT_BLOCKS_SKIP:
            continue
        else:
            raise UnknownFormat("assistant.block:%s" % kind)
    if data.get("isApiErrorMessage") or (isinstance(message, dict) and message.get("model") == "<synthetic>"):
        return []  # 앱이 만든 오류·안내 글. 에이전트가 쓴 것이 아니다
    return groups


def classify_attachment(data):
    attachment = data.get("attachment")
    kind = attachment.get("type") if isinstance(attachment, dict) else type(attachment).__name__
    if kind in ATTACHMENT_TYPES_SKIP:
        return []
    if kind != ATTACHMENT_QUEUED:
        raise UnknownFormat("attachment:%s" % kind)
    origin = attachment.get("origin")
    origin_kind = origin.get("kind") if isinstance(origin, dict) else None
    if origin_kind in USER_ORIGINS_SKIP:
        return []
    if origin_kind != USER_ORIGIN_HUMAN:
        raise UnknownFormat("attachment.queued_command.origin:%s" % origin_kind)
    if attachment.get("isMeta"):
        return []
    text = human_content(attachment.get("prompt"))
    return [("사용자", quote(text))] if text else []


def classify(data):
    """한 줄을 [(누구, 줄들)]로 바꾼다. 실을 것이 없으면 []. 모르는 종류면 UnknownFormat."""
    if data is None:
        raise UnknownFormat("JSON이 아닌 줄")
    kind = data.get("type")
    if kind in LINE_TYPES_SKIP:
        return []
    if kind not in LINE_TYPES_READ:
        raise UnknownFormat("type:%s" % kind)
    if kind == "system":
        subtype = data.get("subtype")
        if subtype not in SYSTEM_SUBTYPES_SKIP:
            raise UnknownFormat("system:%s" % subtype)
        return []
    if kind == "attachment":
        groups = classify_attachment(data)
    elif kind == "user":
        groups = classify_user(data)
    else:
        groups = classify_assistant(data)
    if data.get("isSidechain"):
        return []  # 서브에이전트 안쪽 대화. 메인 세션의 대화가 아니다
    return groups


def render_groups(groups, timestamp):
    blocks = []
    for who, lines in groups:
        blocks.append("**%s** (%s)\n%s" % (who, hhmm(timestamp), "\n".join(lines)))
    return blocks


def find_secret(text):
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return name
    return None


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------

def extract_blocks(projects_dir, session_id, first, last, omitted):
    """범위의 묶음을 [(누구, 찍을 글)]로 낸다. 모르는 형식이나 비밀값 모양이 있으면 하나도 내지 않고 오류를 낸다."""
    path = find_session_file(projects_dir, session_id)
    lines = read_lines(path)
    index = {}
    for position, (_, data) in enumerate(lines):
        if data is not None and isinstance(data.get("uuid"), str):
            index.setdefault(data["uuid"], position)
    for uuid in (first, last):
        if uuid not in index:
            raise ExtractError(EXIT_NOT_FOUND, "uuid를 못 찾음: %s" % uuid)
    start, end = index[first], index[last]
    if start > end:
        raise ExtractError(EXIT_USAGE, "--from이 --to보다 뒤에 있음")
    omitted = list(omitted or [])
    for uuid in omitted:
        if uuid not in index or not start <= index[uuid] <= end:
            raise ExtractError(EXIT_NOT_FOUND, "뺄 uuid가 범위 안에 없음: %s" % uuid)
    omit_set = set(omitted)

    unknown = []
    secrets = []
    blocks = []
    for _, data in lines[start:end + 1]:
        try:
            groups = classify(data)
        except UnknownFormat as error:
            if error.kind not in unknown:
                unknown.append(error.kind)
            continue
        if not groups:
            continue
        uuid = data.get("uuid")
        timestamp = data.get("timestamp")
        if uuid in omit_set:
            groups = [(who, [OMITTED_TEXT]) for who, _ in groups]
            blocks.extend(zip([who for who, _ in groups], render_groups(groups, timestamp)))
            continue
        rendered = render_groups(groups, timestamp)
        name = find_secret("\n".join(rendered))
        if name:
            secrets.append((uuid, name))
            continue
        blocks.extend(zip([who for who, _ in groups], rendered))

    if unknown:
        raise ExtractError(EXIT_UNKNOWN, "\n".join("모르는 형식: %s" % kind for kind in unknown))
    if secrets:
        raise ExtractError(EXIT_SECRET, "\n".join(
            "비밀값 모양(%s): %s" % (name, uuid) for uuid, name in secrets))
    return blocks


def join_blocks(texts):
    return "\n\n".join(texts) + "\n" if texts else ""


def extract_text(projects_dir, session_id, first, last, omitted):
    """발췌 전문. 예전 형식 기록의 표시 사이와, 새 형식의 발췌 파일 범위 묶음이 이 글이다."""
    return join_blocks([text for _, text in extract_blocks(projects_dir, session_id, first, last, omitted)])


def excerpt_line(session_id, first, last):
    return "%sraw/sessions/%s.md %s..%s" % (EXCERPT_PREFIX, session_id, first, last)


def digest_text(session_id, first, last, blocks):
    """새 형식 기록의 표시 사이에 넣는 글. 발췌 위치, 사용자 말, 도구 줄 가운데 Skill과 Read만 남긴다."""
    kept = [excerpt_line(session_id, first, last)]
    for who, text in blocks:
        if who == "사용자":
            kept.append(text)
        elif who == "도구":
            lines = text.split("\n")
            items = [line for line in lines[1:] if DIGEST_TOOL_RE.match(line)]
            if items:
                kept.append("\n".join(lines[:1] + items))
    return join_blocks(kept)


# ---------------------------------------------------------------------------
# 세션 발췌 파일 (raw/sessions/<세션 id>.md)
# ---------------------------------------------------------------------------

def sessions_file(base, session_id):
    return os.path.join(base, *(SESSIONS_DIR + (session_id + ".md",)))


def range_start_line(first, last, omitted):
    extra = " omitted:" + ",".join(sorted(omitted)) if omitted else ""
    return "%s%s..%s%s -->" % (RANGE_START_PREFIX, first, last, extra)


def parse_sections(text, path):
    """발췌 파일의 범위 묶음들. [{first, last, omitted(집합), start, end(줄 위치), body}]"""
    lines = text.replace("\r\n", "\n").split("\n")
    sections = []
    opened = None
    for position, line in enumerate(lines):
        if line.startswith(RANGE_START_PREFIX):
            match = RANGE_START_RE.match(line)
            if opened is not None or not match:
                raise ExtractError(EXIT_MISMATCH, "발췌 파일의 범위 표시가 잘못됨(%d번째 줄): %s" % (position + 1, path))
            opened = {"first": match.group(1), "last": match.group(2), "start": position,
                      "omitted": set(filter(None, (match.group(3) or "").split(",")))}
        elif line == RANGE_END:
            if opened is None:
                raise ExtractError(EXIT_MISMATCH, "발췌 파일의 범위 표시가 잘못됨(%d번째 줄): %s" % (position + 1, path))
            opened["end"] = position
            opened["body"] = "\n".join(lines[opened["start"] + 1:position])
            sections.append(opened)
            opened = None
    if opened is not None:
        raise ExtractError(EXIT_MISMATCH, "발췌 파일의 범위 표시가 닫히지 않음: %s" % path)
    return lines, sections


def find_section(sections, first, last, omitted):
    for section in sections:
        if (section["first"], section["last"], section["omitted"]) == (first, last, set(omitted)):
            return section
    return None


def knowledge_base_for_save(path):
    base = os.path.expanduser(path)
    if not os.path.isdir(os.path.join(base, "raw", "journal")):
        raise ExtractError(EXIT_USAGE, "지식 베이스가 아님(raw/journal 없음): %s" % path)
    return base


def save_excerpt(base, session_id, first, last, omitted, full, replace=False):
    """발췌 전문을 세션 발췌 파일에 범위 묶음으로 적는다. 같은 범위가 이미 있으면 다시 적지 않는다. 한 일을 돌려준다."""
    path = sessions_file(base, session_id)
    if os.path.exists(path):
        lines, sections = parse_sections(read_record(path), path)
    else:
        lines, sections = [
            "# 세션 발췌 %s" % session_id,
            "",
            "`session_extract.py extract --save`가 적는 파일이다. 손으로 고치지 않는다.",
            "범위마다 묶음 하나다. 묶음은 range:start 표시(첫 줄 uuid..끝 줄 uuid)와 range:end 표시 사이다.",
            "기록은 `## 있었던 일`의 발췌 위치 줄로 이 파일의 묶음을 가리킨다.",
            "",
        ], []
    body = full.strip("\n")
    same = find_section(sections, first, last, omitted)
    note = "적음"
    drop = []
    if same is not None:
        if same["body"].strip("\n") == body:
            return "이미 있음"
        if not replace:
            raise ExtractError(EXIT_MISMATCH, "발췌 파일의 그 범위가 다시 뽑은 것과 다름(바꾸려면 --replace): %s" % path)
        drop.append(same)
        note = "바꿈"
    # 같은 범위를 더 많이 빼고 다시 뽑았으면 덜 뺀 묶음은 지운다. 뺀 줄(비밀값)이 파일에 남지 않게 하기 위해서다
    for section in sections:
        if (section["first"], section["last"]) == (first, last) and section["omitted"] < set(omitted):
            drop.append(section)
            note = "적음(덜 뺀 묶음 %d개 지움)" % len([s for s in drop if s is not same])
    for section in sorted(drop, key=lambda item: -item["start"]):
        end = section["end"] + 1
        if end < len(lines) and lines[end] == "":
            end += 1
        del lines[section["start"]:end]
    while lines and lines[-1] == "":
        lines.pop()
    lines += ["", range_start_line(first, last, omitted)] + body.split("\n") + [RANGE_END, ""]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(lines))
    return note


def cmd_extract(args):
    omitted = [uuid for group in (args.omit or []) for uuid in group]
    if args.replace and not args.save:
        raise ExtractError(EXIT_USAGE, "--replace는 --save와 함께 쓴다")
    base = knowledge_base_for_save(args.save) if args.save else None
    blocks = extract_blocks(projects_dir_of(args), args.session, args.first, args.last, omitted)
    full = join_blocks([text for _, text in blocks])
    if base is None:
        sys.stdout.write(full)
        return EXIT_OK
    note = save_excerpt(base, args.session, args.first, args.last, omitted, full, args.replace)
    sys.stderr.write("발췌 파일: raw/sessions/%s.md (%s)\n" % (args.session, note))
    sys.stdout.write(digest_text(args.session, args.first, args.last, blocks))
    return EXIT_OK


# ---------------------------------------------------------------------------
# list, find
# ---------------------------------------------------------------------------

def spoken_lines(path):
    """싣는 줄만 (줄 번호, dict, 묶음들)로 낸다. 모르는 형식은 넘어간다(목록과 검색은 멈추지 않는다)."""
    for number, data in read_lines(path):
        try:
            groups = classify(data)
        except UnknownFormat:
            continue
        if groups:
            yield number, data, groups


def first_chars(lines, limit=80):
    cleaned = []
    for line in lines:
        if line.startswith("> "):
            line = line[2:]
        elif line == ">":
            line = ""
        elif line.startswith("- "):
            line = line[2:]
        cleaned.append(line)
    return one_line(" ".join(cleaned))[:limit]


def stamp(timestamp):
    moment = local_time(timestamp)
    return moment.strftime("%m-%d %H:%M") if moment else "----- --:--"


def parse_hhmm(value):
    match = re.match(r"^(\d{1,2}):(\d{2})$", value or "")
    if not match or int(match.group(1)) > 23 or int(match.group(2)) > 59:
        raise ExtractError(EXIT_USAGE, "시각은 HH:MM으로 적는다: %s" % value)
    return int(match.group(1)) * 60 + int(match.group(2))


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ExtractError(EXIT_USAGE, "날짜는 YYYY-MM-DD로 적는다: %s" % value)


def cmd_list(args):
    path = find_session_file(projects_dir_of(args), args.session)
    around = parse_hhmm(args.around) if args.around else None
    day = parse_date(args.date) if args.date else None
    if args.window < 0:
        raise ExtractError(EXIT_USAGE, "--window는 0 이상")
    for number, data, groups in spoken_lines(path):
        moment = local_time(data.get("timestamp"))
        if day is not None and (moment is None or moment.date() != day):
            continue
        if around is not None:
            if moment is None:
                continue
            gap = abs(moment.hour * 60 + moment.minute - around)
            if min(gap, 1440 - gap) > args.window:
                continue
        for who, lines in groups:
            sys.stdout.write("%d\t%s\t%s\t%s\t%s\n" % (
                number, stamp(data.get("timestamp")), who, first_chars(lines), data.get("uuid")))
    return EXIT_OK


def cmd_find(args):
    needle = one_line(args.text)
    if not needle:
        raise ExtractError(EXIT_USAGE, "--text가 비어 있음")
    day = parse_date(args.date) if args.date else None
    hits = 0
    for path in session_files(projects_dir_of(args)):
        session_id = os.path.basename(path)[:-len(".jsonl")]
        with open(path, encoding="utf-8") as handle:
            for raw in handle:
                # 사용자 말이 있을 수 있는 줄만 푼다(기록 파일이 커서 전부 풀면 느리다)
                if '"user"' not in raw and ATTACHMENT_QUEUED not in raw:
                    continue
                try:
                    data = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(data, dict) or data.get("type") not in ("user", "attachment"):
                    continue
                try:
                    groups = classify(data)
                except UnknownFormat:
                    continue
                for who, lines in groups:
                    if who != "사용자":
                        continue
                    body = "\n".join(line[2:] if line.startswith("> ") else "" for line in lines)
                    if needle not in one_line(body):
                        continue
                    moment = local_time(data.get("timestamp"))
                    if day is not None and (moment is None or moment.date() != day):
                        continue
                    when = moment.strftime("%Y-%m-%d %H:%M") if moment else "-"
                    sys.stdout.write("%s\t%s\t%s\t%s\n" % (
                        session_id, data.get("uuid"), when, first_chars(lines)))
                    hits += 1
    if not hits:
        raise ExtractError(EXIT_NOT_FOUND, "그 글이 들어 있는 사용자 말을 못 찾음")
    return EXIT_OK


# ---------------------------------------------------------------------------
# verify, confirm
# ---------------------------------------------------------------------------

def read_record(path):
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            return handle.read()
    except OSError as error:
        raise ExtractError(EXIT_USAGE, "기록 파일을 못 읽음: %s (%s)" % (path, error.strerror))


def front_matter_span(text):
    """머리말 줄들의 (시작, 끝) 줄 번호. 없으면 None."""
    lines = text.split("\n")
    if not lines or lines[0].rstrip("\r") != "---":
        return None
    for position in range(1, len(lines)):
        if lines[position].rstrip("\r") == "---":
            return 1, position
    return None


def clean_value(value):
    value = re.sub(r"\s+#.*$", "", value.strip())
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value.strip()


def parse_front_matter(text):
    span = front_matter_span(text)
    if span is None:
        raise ExtractError(EXIT_USAGE, "머리말이 없음")
    lines = [line.rstrip("\r") for line in text.split("\n")[span[0]:span[1]]]
    fields = {}
    position = 0
    while position < len(lines):
        match = re.match(r"^([A-Za-z_][\w\-]*):(.*)$", lines[position])
        position += 1
        if not match:
            continue
        key, value = match.group(1), clean_value(match.group(2))
        if key == "omitted":
            items = []
            if value.startswith("["):
                items = [clean_value(item) for item in value.strip("[]").split(",")]
            elif not value:
                while position < len(lines) and re.match(r"^\s*-\s+", lines[position]):
                    items.append(clean_value(re.sub(r"^\s*-\s+", "", lines[position])))
                    position += 1
            fields[key] = [item for item in items if item]
        else:
            fields[key] = value
    return fields


def marked_block(text):
    """표시 두 개 사이의 글. 표시가 없으면 None."""
    lines = text.replace("\r\n", "\n").split("\n")
    try:
        start = lines.index(MARK_START)
        end = lines.index(MARK_END, start + 1)
    except ValueError:
        return None
    return "\n".join(lines[start + 1:end])


def compare_lines(have, want, where, name):
    """줄 단위로 글자까지 같아야 한다. 다르면 처음 다른 줄을 알리고 종료 코드 5를 낸다."""
    if have == want:
        return
    for number in range(max(len(have), len(want))):
        left = have[number] if number < len(have) else None
        right = want[number] if number < len(want) else None
        if left != right:
            raise ExtractError(EXIT_MISMATCH, "%s %d번째 줄부터 다름 (%s %d줄, 다시 뽑은 것 %d줄)" % (
                where, number + 1, name, len(have), len(want)))


def knowledge_base_of(record_path, given):
    """새 형식 기록의 발췌 파일이 있는 지식 베이스. 준 값, 기록 파일의 위쪽 폴더, 환경 변수 순서로 찾는다."""
    if given:
        return os.path.expanduser(given)
    folder = os.path.dirname(os.path.abspath(record_path))
    while True:
        if os.path.isdir(os.path.join(folder, "raw", "journal")):
            return folder
        parent = os.path.dirname(folder)
        if parent == folder:
            break
        folder = parent
    if os.environ.get(KB_ENV):
        return os.path.expanduser(os.environ[KB_ENV])
    raise ExtractError(EXIT_USAGE, "지식 베이스를 못 찾음. --knowledge-base로 준다")


def verify_record(path, projects_dir, knowledge_base=None):
    """통과하면 설명 글을 돌려준다. 통과 못 하면 ExtractError."""
    text = read_record(path)
    fields = parse_front_matter(text)
    if fields.get("source") == "memo":
        return "source: memo라 대조할 세션 기록이 없음"
    if fields.get("source") == "agent":
        # 자가 발전이 스스로 정한 구조 결정 기록. 사용자 말이 없어 처음부터 active로 만든다. 여기서 통과시키지 않는다
        raise ExtractError(EXIT_USAGE, "source: agent 기록은 verify와 confirm의 대상이 아님")
    session = fields.get("session") or "-"
    span = fields.get("range") or "-"
    block = marked_block(text)
    if session == "-" or ".." not in span or block is None:
        raise ExtractError(EXIT_MISMATCH, "session, range, 표시 두 개가 다 있어야 함")
    first, last = [part.strip() for part in span.split("..", 1)]
    omitted = fields.get("omitted") or []
    blocks = extract_blocks(projects_dir, session, first, last, omitted)
    full = join_blocks([part for _, part in blocks])
    have = block.strip("\n").split("\n")
    if not have[0].startswith(EXCERPT_PREFIX):
        # 예전 형식: 표시 사이가 발췌 전문이다
        compare_lines(have, full.strip("\n").split("\n"), "표시 사이", "기록")
        return "일치"
    # 새 형식: 표시 사이는 줄인 글이고 전문은 발췌 파일에 있다. 둘 다 다시 뽑은 것과 같아야 한다
    compare_lines(have, digest_text(session, first, last, blocks).strip("\n").split("\n"), "표시 사이", "기록")
    excerpts = sessions_file(knowledge_base_of(path, knowledge_base), session)
    if not os.path.isfile(excerpts):
        raise ExtractError(EXIT_MISMATCH, "발췌 파일이 없음: raw/sessions/%s.md" % session)
    section = find_section(parse_sections(read_record(excerpts), excerpts)[1], first, last, omitted)
    if section is None:
        raise ExtractError(EXIT_MISMATCH, "발췌 파일에 그 범위(와 같은 omitted)의 묶음이 없음: raw/sessions/%s.md %s..%s" % (
            session, first, last))
    compare_lines(section["body"].strip("\n").split("\n"), full.strip("\n").split("\n"), "발췌 파일의 범위 묶음", "발췌 파일")
    return "일치(표시 사이와 발췌 파일)"


def cmd_verify(args):
    note = verify_record(args.record, projects_dir_of(args), getattr(args, "knowledge_base", None))
    sys.stdout.write("통과\t%s\t%s\n" % (args.record, note))
    return EXIT_OK


def set_active(path):
    """머리말의 status: draft를 active로 바꾼다. 다른 글자는 건드리지 않는다. 결과 글을 돌려준다."""
    text = read_record(path)
    span = front_matter_span(text)
    lines = text.split("\n")
    for position in range(span[0], span[1]):
        match = re.match(r"^(status:\s*[\"']?)([A-Za-z]+)", lines[position])
        if not match:
            continue
        if match.group(2) == "active":
            return "이미 active"
        if match.group(2) != "draft":
            raise ExtractError(EXIT_USAGE, "status가 draft가 아님: %s" % match.group(2))
        lines[position] = match.group(1) + "active" + lines[position][match.end():]
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write("\n".join(lines))
        return "active로 바꿈"
    raise ExtractError(EXIT_USAGE, "머리말에 status가 없음")


def cmd_confirm(args):
    result = EXIT_OK
    for path in args.records:
        try:
            verify_record(path, projects_dir_of(args), getattr(args, "knowledge_base", None))
            note = set_active(path)
            sys.stdout.write("통과\t%s\t%s\n" % (path, note))
        except ExtractError as error:
            sys.stdout.write("실패(코드 %d)\t%s\t%s\n" % (
                error.code, path, error.message.replace("\n", "; ")))
            if result == EXIT_OK:
                result = error.code
    return result


# ---------------------------------------------------------------------------
# pending
# ---------------------------------------------------------------------------

def pending_memo_lines(text):
    """마지막 `정리됨:` 줄 뒤에 있는 메모 줄 수. 그 줄이 없으면 파일의 메모 줄 전부다."""
    count = 0
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith(DONE_PREFIX):
            count = 0
        elif line:
            count += 1
    return count


def cmd_pending(args):
    base = os.path.expanduser(args.knowledge_base)
    journal = os.path.join(base, "raw", "journal")
    if not os.path.isdir(journal):
        raise ExtractError(EXIT_USAGE, "지식 베이스가 아님(raw/journal 없음): %s" % args.knowledge_base)
    memo_total = 0
    for name in sorted(os.listdir(journal)):
        if not (name.endswith(".md") and name[:1].isdigit()):
            continue
        count = pending_memo_lines(read_record(os.path.join(journal, name)))
        if count:
            sys.stdout.write("메모\traw/journal/%s\t%d\n" % (name, count))
            memo_total += count
    draft_total = 0
    for folder in RECORD_DIRS:
        path = os.path.join(base, "raw", folder)
        if not os.path.isdir(path):
            continue
        for name in sorted(os.listdir(path)):
            if not name.endswith(".md"):
                continue
            text = read_record(os.path.join(path, name))
            if front_matter_span(text) and parse_front_matter(text).get("status") == "draft":
                sys.stdout.write("draft\traw/%s/%s\n" % (folder, name))
                draft_total += 1
    sys.stdout.write("합계\t메모 %d\tdraft %d\n" % (memo_total, draft_total))
    return EXIT_OK


# ---------------------------------------------------------------------------
# 명령줄
# ---------------------------------------------------------------------------

class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("사용법 오류: %s\n" % message)
        sys.exit(EXIT_USAGE)


def build_parser():
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--projects-dir", default=argparse.SUPPRESS,
                        help="세션 기록 폴더 (기본 ~/.claude/projects)")
    parser = Parser(description="세션 기록에서 정해진 범위를 그대로 뽑는다", parents=[shared])
    commands = parser.add_subparsers(dest="command")

    find = commands.add_parser("find", parents=[shared], help="사용자 말에 그 글이 들어 있는 세션과 줄을 찾는다")
    find.add_argument("--text", required=True)
    find.add_argument("--date", help="YYYY-MM-DD (이 컴퓨터의 시간대)")
    find.set_defaults(run=cmd_find)

    lister = commands.add_parser("list", parents=[shared], help="범위를 고르기 위한 줄 목록")
    lister.add_argument("--session", required=True)
    lister.add_argument("--around", help="HH:MM")
    lister.add_argument("--window", type=int, default=30, help="앞뒤 몇 분 (기본 30)")
    lister.add_argument("--date", help="YYYY-MM-DD. 여러 날에 걸친 세션에서 하루만 볼 때")
    lister.set_defaults(run=cmd_list)

    extract = commands.add_parser("extract", parents=[shared], help="범위를 마크다운으로 찍는다")
    extract.add_argument("--session", required=True)
    extract.add_argument("--from", dest="first", required=True)
    extract.add_argument("--to", dest="last", required=True)
    extract.add_argument("--omit", nargs="+", action="append", metavar="UUID")
    extract.add_argument("--save", metavar="지식 베이스",
                         help="발췌 전문을 raw/sessions/<세션 id>.md에 적고, 기록의 표시 사이에 넣을 글을 찍는다")
    extract.add_argument("--replace", action="store_true",
                         help="--save와 함께. 같은 범위의 묶음이 다시 뽑은 것과 다르면 바꾼다")
    extract.set_defaults(run=cmd_extract)

    verify = commands.add_parser("verify", parents=[shared], help="기록 파일을 다시 뽑은 것과 비교한다")
    verify.add_argument("record")
    verify.add_argument("--knowledge-base", help="새 형식 기록의 발췌 파일이 있는 지식 베이스 (기본: 기록 파일의 위쪽 폴더)")
    verify.set_defaults(run=cmd_verify)

    confirm = commands.add_parser("confirm", parents=[shared], help="verify가 통과한 기록을 active로 바꾼다")
    confirm.add_argument("records", nargs="+")
    confirm.add_argument("--knowledge-base", help="새 형식 기록의 발췌 파일이 있는 지식 베이스 (기본: 기록 파일의 위쪽 폴더)")
    confirm.set_defaults(run=cmd_confirm)

    pending = commands.add_parser("pending", parents=[shared], help="정리 안 된 메모 줄 수와 draft 기록 수를 찍는다")
    pending.add_argument("knowledge_base", help="지식 베이스 폴더")
    pending.set_defaults(run=cmd_pending)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "run", None):
        parser.error("명령이 없음 (find, list, extract, verify, confirm, pending)")
    try:
        return args.run(args)
    except ExtractError as error:
        sys.stderr.write(error.message + "\n")
        return error.code


if __name__ == "__main__":
    sys.exit(main())
