#!/usr/bin/env python3
"""세션 기록(jsonl)에서 정해진 범위를 그대로 뽑는다.

명령: find, list, extract, verify, confirm
종료 코드: 0 성공, 1 사용법 오류, 2 세션이나 uuid를 못 찾음, 3 모르는 형식,
          4 비밀값 모양, 5 verify 불일치

세션 기록은 <projects-dir>/*/<세션 id>.jsonl 이다. 폴더 이름이 아니라 세션 id로 찾는다.
파이썬 표준 라이브러리만 쓴다.
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

def extract_text(projects_dir, session_id, first, last, omitted):
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
            blocks.extend(render_groups(groups, timestamp))
            continue
        rendered = render_groups(groups, timestamp)
        name = find_secret("\n".join(rendered))
        if name:
            secrets.append((uuid, name))
            continue
        blocks.extend(rendered)

    if unknown:
        raise ExtractError(EXIT_UNKNOWN, "\n".join("모르는 형식: %s" % kind for kind in unknown))
    if secrets:
        raise ExtractError(EXIT_SECRET, "\n".join(
            "비밀값 모양(%s): %s" % (name, uuid) for uuid, name in secrets))
    return "\n\n".join(blocks) + "\n" if blocks else ""


def cmd_extract(args):
    omitted = [uuid for group in (args.omit or []) for uuid in group]
    text = extract_text(projects_dir_of(args), args.session, args.first, args.last, omitted)
    sys.stdout.write(text)
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


def verify_record(path, projects_dir):
    """통과하면 설명 글을 돌려준다. 통과 못 하면 ExtractError."""
    text = read_record(path)
    fields = parse_front_matter(text)
    if fields.get("source") == "memo":
        return "source: memo라 대조할 세션 기록이 없음"
    session = fields.get("session") or "-"
    span = fields.get("range") or "-"
    block = marked_block(text)
    if session == "-" or ".." not in span or block is None:
        raise ExtractError(EXIT_MISMATCH, "session, range, 표시 두 개가 다 있어야 함")
    first, last = [part.strip() for part in span.split("..", 1)]
    expected = extract_text(projects_dir, session, first, last, fields.get("omitted") or [])
    have = block.strip("\n").split("\n")
    want = expected.strip("\n").split("\n")
    if have != want:
        for number in range(max(len(have), len(want))):
            left = have[number] if number < len(have) else None
            right = want[number] if number < len(want) else None
            if left != right:
                raise ExtractError(EXIT_MISMATCH, "표시 사이 %d번째 줄부터 다름 (기록 %d줄, 다시 뽑은 것 %d줄)" % (
                    number + 1, len(have), len(want)))
    return "일치"


def cmd_verify(args):
    note = verify_record(args.record, projects_dir_of(args))
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
            verify_record(path, projects_dir_of(args))
            note = set_active(path)
            sys.stdout.write("통과\t%s\t%s\n" % (path, note))
        except ExtractError as error:
            sys.stdout.write("실패(코드 %d)\t%s\t%s\n" % (
                error.code, path, error.message.replace("\n", "; ")))
            if result == EXIT_OK:
                result = error.code
    return result


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
    extract.set_defaults(run=cmd_extract)

    verify = commands.add_parser("verify", parents=[shared], help="기록 파일을 다시 뽑은 것과 비교한다")
    verify.add_argument("record")
    verify.set_defaults(run=cmd_verify)

    confirm = commands.add_parser("confirm", parents=[shared], help="verify가 통과한 기록을 active로 바꾼다")
    confirm.add_argument("records", nargs="+")
    confirm.set_defaults(run=cmd_confirm)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "run", None):
        parser.error("명령이 없음 (find, list, extract, verify, confirm)")
    try:
        return args.run(args)
    except ExtractError as error:
        sys.stderr.write(error.message + "\n")
        return error.code


if __name__ == "__main__":
    sys.exit(main())
