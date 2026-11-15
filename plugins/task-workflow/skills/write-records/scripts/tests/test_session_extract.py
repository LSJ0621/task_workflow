"""session_extract.py 시험.

세션 기록은 전부 지어낸 것이다(fixtures/projects). 싣지 않아야 하는 글에는 MARKER라는 낱말을 넣어 두었다.
돌리기: python3 -m unittest discover -s <이 폴더>
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "session_extract.py")
FIXTURES = os.path.join(HERE, "fixtures", "projects")
FOLDER = "-fake-home-proj-a"
SID = "11111111-1111-4111-8111-111111111111"
SID2 = "22222222-2222-4222-8222-222222222222"


def uid(number):
    return "00000000-0000-4000-8000-%012d" % number


FIRST, LAST = uid(1), uid(45)


def run(args, projects=FIXTURES, tz="Asia/Seoul"):
    env = dict(os.environ, TZ=tz, PYTHONIOENCODING="utf-8")
    done = subprocess.run(
        [sys.executable, SCRIPT, "--projects-dir", projects] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")


def extract(first=FIRST, last=LAST, session=SID, extra=(), **kwargs):
    return run(["extract", "--session", session, "--from", first, "--to", last] + list(extra), **kwargs)


def human(number, text, minute=0):
    return {"type": "user", "uuid": uid(number), "timestamp": "2026-02-03T02:%02d:00.000Z" % minute,
            "sessionId": SID2, "isSidechain": False, "origin": {"kind": "human"},
            "turnOrigin": "human", "promptSource": "typed",
            "message": {"role": "user", "content": text}}


def agent(number, blocks, minute=0):
    return {"type": "assistant", "uuid": uid(number), "timestamp": "2026-02-03T02:%02d:30.000Z" % minute,
            "sessionId": SID2, "isSidechain": False,
            "message": {"role": "assistant", "model": "claude-fake-1", "content": blocks}}


class TempProjects(unittest.TestCase):
    """시험마다 빈 세션 기록 폴더를 하나 만든다."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="session-extract-test-")
        self.projects = os.path.join(self.tmp, "projects")
        os.makedirs(self.projects)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write_session(self, rows, session=SID2, folder="-fake-other"):
        target = os.path.join(self.projects, folder)
        os.makedirs(target, exist_ok=True)
        path = os.path.join(target, session + ".jsonl")
        with open(path, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return path

    def copy_fixture(self, folder=FOLDER):
        target = os.path.join(self.projects, folder)
        os.makedirs(target, exist_ok=True)
        path = os.path.join(target, SID + ".jsonl")
        shutil.copy(os.path.join(FIXTURES, FOLDER, SID + ".jsonl"), path)
        return path

    def write_record(self, body, first=FIRST, last=LAST, session=SID, omitted="[]",
                     status="draft", source="session", name="C-20260105-01.md"):
        text = (
            "---\n"
            "id: C-20260105-01\n"
            "status: %s          # draft(확인 전) | active | superseded\n"
            "source: %s\n"
            "session: %s\n"
            "range: %s..%s\n"
            "omitted: %s\n"
            "memo: 2026-01-05 10:21\n"
            "---\n"
            "# 줄 간격을 한 곳만 고쳤다\n"
            "\n"
            "## 있었던 일\n"
            "<!-- extract:start -->\n"
            "%s"
            "<!-- extract:end -->\n"
            "\n"
            "## 요지\n"
            "### 어떤 작업에서\n"
            "목록 화면 간격 고치기. status: draft 라는 글자가 본문에도 있다.\n"
            "\n"
            "## 분석\n"
            "아직 없음\n"
        ) % (status, source, session, first, last, omitted, body)
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        return path


class ExtractTest(unittest.TestCase):

    def test_exact_output_of_small_range(self):
        code, out, err = extract(FIRST, uid(11))
        self.assertEqual(code, 0, err)
        self.assertEqual(out, (
            "**사용자** (10:00)\n"
            "> 목록 화면의 줄 간격을 넓혀 줘.\n"
            ">\n"
            "> 지금은 너무 좁아.\n"
            "\n"
            "**에이전트** (10:00)\n"
            "> 먼저 화면 파일을 보겠습니다.\n"
            "\n"
            "**도구** (10:01)\n"
            "- Skill: fake-plugin:build-screens\n"
            "\n"
            "**도구** (10:01)\n"
            "- Read: /fake/home/proj-a/src/list_screen.txt\n"
            "\n"
            "**도구** (10:02)\n"
            "- Bash: 화면 시험을 돌린다\n"
        ))

    def test_nothing_inserted_by_system_is_printed(self):
        # 알림, 훅 출력, 도구 결과, 생각 과정, 작업 알림, 요약, 명령어 본문에는 전부 MARKER가 들어 있다
        code, out, err = extract()
        self.assertEqual(code, 0, err)
        self.assertNotIn("MARKER", out)
        self.assertNotIn("system-reminder", out)
        self.assertNotIn("task-notification", out)
        self.assertNotIn("artifact-view-context", out)
        self.assertNotIn("Request interrupted", out)

    def test_user_text_keeps_only_what_user_typed(self):
        code, out, _ = extract(uid(26), uid(33))
        self.assertEqual(code, 0)
        self.assertIn("**사용자** (10:21)\n> 아직 좁아. 제목 아래 간격도 봐.\n", out)
        self.assertIn("**사용자** (10:22)\n> 여기 이 부분 말이야.\n", out)
        self.assertIn("**사용자** (10:23)\n> [이미지]\n> 이 그림처럼 해 줘.\n", out)
        self.assertIn("**사용자** (10:24)\n> /fake-plugin:verify-work 목록 화면\n", out)

    def test_user_text_typed_while_agent_was_working(self):
        code, out, _ = extract(uid(28), uid(30))
        self.assertEqual(code, 0)
        self.assertIn("**사용자** (10:21)\n> 아, 그리고 제목은 굵게 해 줘.\n", out)
        self.assertEqual(out.count("**사용자**"), 1)

    def test_tool_calls_print_only_agreed_fields(self):
        code, out, _ = extract()
        self.assertEqual(code, 0)
        for line in (
            "- Skill: fake-plugin:build-screens",
            "- Read: /fake/home/proj-a/src/list_screen.txt",
            "- Bash: 화면 시험을 돌린다",
            "- Agent: Explore | 간격 값을 쓰는 곳 찾기",
            "- Edit: /fake/home/proj-a/src/list_screen.txt",
            "- Write: /fake/home/proj-a/notes/spacing.md",
            "- mcp__fake__lookup",
            "- Bash",
            "- Agent: - | 고친 화면 확인",
        ):
            self.assertIn("\n" + line + "\n", out)
        self.assertNotIn("run-tests", out)
        self.assertNotIn("query", out)

    def test_text_and_tools_in_one_line_make_two_blocks(self):
        code, out, _ = extract(uid(42), uid(42))
        self.assertEqual(code, 0)
        self.assertEqual(out, (
            "**에이전트** (10:28)\n"
            "> 제목을 굵게 하고 간격을 맞췄습니다.\n"
            "\n"
            "**도구** (10:28)\n"
            "- Read: /fake/home/proj-a/src/title.txt\n"
            "- Agent: - | 고친 화면 확인\n"
        ))

    def test_same_input_gives_same_output(self):
        self.assertEqual(extract()[1], extract()[1])

    def test_time_is_local(self):
        self.assertIn("**사용자** (01:00)", extract(FIRST, FIRST, tz="UTC")[1])
        self.assertIn("**사용자** (10:00)", extract(FIRST, FIRST)[1])

    def test_omit_prints_placeholder(self):
        code, out, _ = extract(FIRST, uid(11), extra=["--omit", uid(5), uid(11)])
        self.assertEqual(code, 0)
        self.assertIn("**에이전트** (10:00)\n> [비밀값이 있어 뺌]\n", out)
        self.assertIn("**도구** (10:02)\n> [비밀값이 있어 뺌]\n", out)
        self.assertNotIn("먼저 화면 파일을", out)
        self.assertNotIn("화면 시험을 돌린다", out)
        self.assertIn("- Skill: fake-plugin:build-screens", out)

    def test_omit_outside_range_is_not_found(self):
        self.assertEqual(extract(FIRST, uid(5), extra=["--omit", uid(23)])[0], 2)

    def test_not_found(self):
        self.assertEqual(extract(session="99999999-9999-4999-8999-999999999999")[0], 2)
        self.assertEqual(extract(FIRST, uid(999))[0], 2)
        self.assertEqual(extract(uid(999), LAST)[0], 2)

    def test_usage_errors(self):
        self.assertEqual(run([])[0], 1)
        self.assertEqual(run(["extract", "--session", SID])[0], 1)
        self.assertEqual(run(["nonsense"])[0], 1)
        self.assertEqual(extract(uid(23), FIRST)[0], 1)


class LongTextTest(TempProjects):

    def test_long_text_is_not_cut(self):
        long_user = "\n".join("사용자 %d번째 줄 " % number + "가" * 200 for number in range(300))
        long_agent = "나" * 50000
        long_desc = "설명 " + "다" * 3000
        self.write_session([
            human(1, long_user),
            agent(2, [{"type": "text", "text": long_agent}]),
            agent(3, [{"type": "tool_use", "id": "t1", "name": "Bash",
                       "input": {"command": "x", "description": long_desc}}]),
        ])
        code, out, err = run(["extract", "--session", SID2, "--from", uid(1), "--to", uid(3)],
                             projects=self.projects)
        self.assertEqual(code, 0, err)
        self.assertEqual(out.count("가"), 300 * 200)
        self.assertIn("> 사용자 299번째 줄 ", out)
        self.assertIn("> " + long_agent + "\n", out)
        self.assertIn("- Bash: " + long_desc + "\n", out)


class SecretTest(TempProjects):

    def setUp(self):
        TempProjects.setUp(self)
        # 저장소에 비밀값처럼 보이는 글자를 두지 않으려고 여기서 이어 붙인다
        self.shapes = [
            "s" + "k-" + "abcDEF0123456789abcDEF",
            "AK" + "IA" + "ABCDEFGHIJKLMNOP",
            "gh" + "p_" + "abcdefghijklmnopqrstuvwxyz0123",
            "-----BEGIN " + "RSA PRIVATE KEY-----",
            "pass" + "word=" + "hunter2hunter2",
            "to" + "ken=" + "abcdef123456",
        ]

    def test_each_secret_shape_stops_output(self):
        for position, shape in enumerate(self.shapes):
            self.write_session([human(1, "앞 글"), human(2, "이걸 써: " + shape), human(3, "뒤 글")])
            code, out, err = run(["extract", "--session", SID2, "--from", uid(1), "--to", uid(3)],
                                 projects=self.projects)
            self.assertEqual(code, 4, "모양 %d" % position)
            self.assertEqual(out, "")
            self.assertIn(uid(2), err)
            self.assertNotIn(uid(1), err)
            self.assertNotIn(shape, err)

    def test_secret_in_agent_text_and_tool_field(self):
        self.write_session([
            human(1, "보여 줘"),
            agent(2, [{"type": "text", "text": "값은 " + self.shapes[1] + " 입니다"}]),
            agent(3, [{"type": "tool_use", "id": "t1", "name": "Bash",
                       "input": {"command": "x", "description": "쓴다 " + self.shapes[5]}}]),
        ])
        code, out, err = run(["extract", "--session", SID2, "--from", uid(1), "--to", uid(3)],
                             projects=self.projects)
        self.assertEqual(code, 4)
        self.assertIn(uid(2), err)
        self.assertIn(uid(3), err)

    def test_omit_lets_the_rest_through(self):
        self.write_session([human(1, "앞 글"), human(2, "이걸 써: " + self.shapes[0]), human(3, "뒤 글")])
        code, out, err = run(["extract", "--session", SID2, "--from", uid(1), "--to", uid(3),
                              "--omit", uid(2)], projects=self.projects)
        self.assertEqual(code, 0, err)
        self.assertIn("> 앞 글", out)
        self.assertIn("> [비밀값이 있어 뺌]", out)
        self.assertIn("> 뒤 글", out)
        self.assertNotIn(self.shapes[0], out)

    def test_secret_in_unprinted_field_does_not_stop(self):
        self.write_session([
            human(1, "돌려 줘"),
            agent(2, [{"type": "tool_use", "id": "t1", "name": "Bash",
                       "input": {"command": "export X=" + self.shapes[1], "description": "값을 넣는다"}}]),
        ])
        code, out, _ = run(["extract", "--session", SID2, "--from", uid(1), "--to", uid(2)],
                           projects=self.projects)
        self.assertEqual(code, 0)
        self.assertNotIn(self.shapes[1], out)

    def test_ordinary_words_are_not_secrets(self):
        self.write_session([
            human(1, "task-workflow 스킬의 token 수와 password 규칙을 설명해 줘. token= 뒤는 비어 있어."),
            agent(2, [{"type": "tool_use", "id": "t1", "name": "Skill",
                       "input": {"skill": "task-workflow:build-screens"}}]),
        ])
        code, _, err = run(["extract", "--session", SID2, "--from", uid(1), "--to", uid(2)],
                           projects=self.projects)
        self.assertEqual(code, 0, err)


class UnknownFormatTest(TempProjects):

    def check(self, row, name):
        self.write_session([human(1, "앞 글"), row, human(3, "뒤 글")])
        code, out, err = run(["extract", "--session", SID2, "--from", uid(1), "--to", uid(3)],
                             projects=self.projects)
        self.assertEqual(code, 3, err)
        self.assertEqual(out, "")
        self.assertIn(name, err)

    def test_unknown_line_type(self):
        self.check({"type": "brand-new-line", "sessionId": SID2}, "type:brand-new-line")

    def test_unknown_system_subtype(self):
        self.check({"type": "system", "subtype": "brand_new", "uuid": uid(2)}, "system:brand_new")

    def test_unknown_attachment_type(self):
        self.check({"type": "attachment", "uuid": uid(2), "attachment": {"type": "brand_new"}},
                   "attachment:brand_new")

    def test_unknown_assistant_block(self):
        self.check(agent(2, [{"type": "brand_new_block", "data": "x"}]), "assistant.block:brand_new_block")

    def test_unknown_user_block(self):
        row = human(2, [{"type": "document", "source": {}}])
        self.check(row, "user.block:document")

    def test_unknown_user_origin(self):
        row = human(2, "글")
        row["origin"] = {"kind": "brand-new-origin"}
        self.check(row, "user.origin:brand-new-origin")

    def test_user_line_without_origin_is_not_dropped_silently(self):
        row = human(2, "origin 칸이 없는 글")
        del row["origin"], row["turnOrigin"], row["promptSource"]
        self.check(row, "origin 없음")

    def test_unknown_inserted_tag_in_user_text(self):
        self.check(human(2, "<brand-new-note>끼워 넣은 것</brand-new-note>\n내 말"), "user.tag:brand-new-note")

    def test_line_that_is_not_json(self):
        path = self.write_session([human(1, "앞 글"), human(3, "뒤 글")])
        with open(path, encoding="utf-8") as handle:
            rows = handle.read().split("\n")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(rows[0] + "\n{깨진 줄\n" + rows[1] + "\n")
        code, _, err = run(["extract", "--session", SID2, "--from", uid(1), "--to", uid(3)],
                           projects=self.projects)
        self.assertEqual(code, 3)
        self.assertIn("JSON", err)

    def test_unknown_outside_range_does_not_matter(self):
        self.write_session([human(1, "앞 글"), human(2, "가운데"), {"type": "brand-new-line"}, human(4, "뒤")])
        code, out, _ = run(["extract", "--session", SID2, "--from", uid(1), "--to", uid(2)],
                           projects=self.projects)
        self.assertEqual(code, 0)
        self.assertIn("> 가운데", out)

    def test_list_and_find_do_not_stop_on_unknown(self):
        self.write_session([human(1, "앞 글"), {"type": "brand-new-line"}, human(3, "뒤 글")])
        code, out, _ = run(["list", "--session", SID2], projects=self.projects)
        self.assertEqual(code, 0)
        self.assertEqual(len(out.strip().split("\n")), 2)
        self.assertEqual(run(["find", "--text", "뒤 글"], projects=self.projects)[0], 0)


class VerifyConfirmTest(TempProjects):

    def setUp(self):
        TempProjects.setUp(self)
        self.session_path = self.copy_fixture()
        code, self.body, err = extract(projects=self.projects)
        self.assertEqual(code, 0, err)

    def read(self, path):
        with open(path, encoding="utf-8", newline="") as handle:
            return handle.read()

    def test_verify_passes(self):
        record = self.write_record(self.body)
        code, out, err = run(["verify", record], projects=self.projects)
        self.assertEqual(code, 0, err)
        self.assertIn("통과", out)

    def test_verify_fails_when_one_character_differs(self):
        record = self.write_record(self.body.replace("너무 좁아", "너무 좁아!"))
        code, _, err = run(["verify", record], projects=self.projects)
        self.assertEqual(code, 5)
        self.assertIn("4번째 줄", err)

    def test_verify_fails_when_a_block_is_missing_or_added(self):
        missing = self.body.replace("**도구** (10:03)\n- mcp__fake__lookup\n\n", "")
        self.assertNotEqual(missing, self.body)
        self.assertEqual(run(["verify", self.write_record(missing)], projects=self.projects)[0], 5)
        added = self.body + "\n**사용자** (09:01)\n> 하지 않은 말\n"
        self.assertEqual(run(["verify", self.write_record(added)], projects=self.projects)[0], 5)

    def test_verify_fails_when_range_in_header_differs(self):
        record = self.write_record(self.body, last=uid(23))
        self.assertEqual(run(["verify", record], projects=self.projects)[0], 5)

    def test_verify_uses_omitted_from_header(self):
        code, body, _ = extract(projects=self.projects, extra=["--omit", uid(5), uid(23)])
        self.assertEqual(code, 0)
        inline = self.write_record(body, omitted="[%s, %s]" % (uid(5), uid(23)))
        self.assertEqual(run(["verify", inline], projects=self.projects)[0], 0)
        block = self.write_record(body, omitted="\n  - %s\n  - %s" % (uid(5), uid(23)), name="X-1.md")
        self.assertEqual(run(["verify", block], projects=self.projects)[0], 0)
        without = self.write_record(body, name="X-2.md")
        self.assertEqual(run(["verify", without], projects=self.projects)[0], 5)

    def test_verify_when_session_record_is_gone(self):
        record = self.write_record(self.body)
        os.remove(self.session_path)
        self.assertEqual(run(["verify", record], projects=self.projects)[0], 2)

    def test_verify_when_uuid_is_gone(self):
        record = self.write_record(self.body, last=uid(999))
        self.assertEqual(run(["verify", record], projects=self.projects)[0], 2)

    def test_verify_without_marks_fails(self):
        record = self.write_record(self.body)
        text = self.read(record).replace("<!-- extract:end -->\n", "")
        with open(record, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        self.assertEqual(run(["verify", record], projects=self.projects)[0], 5)

    def test_verify_missing_record_file_is_usage_error(self):
        self.assertEqual(run(["verify", os.path.join(self.tmp, "없는-파일.md")], projects=self.projects)[0], 1)

    def test_session_is_found_after_folder_changes(self):
        record = self.write_record(self.body)
        moved = os.path.join(self.projects, "-fake-moved-somewhere-else")
        os.makedirs(moved)
        shutil.move(self.session_path, os.path.join(moved, SID + ".jsonl"))
        code, body, _ = extract(projects=self.projects)
        self.assertEqual(code, 0)
        self.assertEqual(body, self.body)
        self.assertEqual(run(["verify", record], projects=self.projects)[0], 0)

    def test_confirm_changes_only_the_status_word(self):
        record = self.write_record(self.body)
        before = self.read(record)
        code, out, err = run(["confirm", record], projects=self.projects)
        self.assertEqual(code, 0, err)
        after = self.read(record)
        self.assertEqual(after, before.replace("status: draft ", "status: active ", 1))
        self.assertIn("status: active          # draft(확인 전)", after)
        self.assertIn("status: draft 라는 글자가 본문에도 있다", after)
        self.assertEqual(run(["verify", record], projects=self.projects)[0], 0)

    def test_confirm_leaves_failed_record_alone(self):
        good = self.write_record(self.body, name="C-good.md")
        bad = self.write_record(self.body.replace("그대로 두겠습니다", "그대로 둘게요"), name="C-bad.md")
        before = self.read(bad)
        code, out, _ = run(["confirm", bad, good], projects=self.projects)
        self.assertEqual(code, 5)
        self.assertEqual(self.read(bad), before)
        self.assertIn("status: active", self.read(good))
        self.assertIn("실패(코드 5)\t" + bad, out)
        self.assertIn("통과\t" + good, out)

    def test_confirm_twice_keeps_file(self):
        record = self.write_record(self.body)
        self.assertEqual(run(["confirm", record], projects=self.projects)[0], 0)
        once = self.read(record)
        code, out, _ = run(["confirm", record], projects=self.projects)
        self.assertEqual(code, 0)
        self.assertEqual(self.read(record), once)
        self.assertIn("이미 active", out)

    def test_confirm_when_session_is_gone(self):
        record = self.write_record(self.body)
        before = self.read(record)
        os.remove(self.session_path)
        self.assertEqual(run(["confirm", record], projects=self.projects)[0], 2)
        self.assertEqual(self.read(record), before)

    def test_memo_record_has_nothing_to_compare(self):
        path = os.path.join(self.tmp, "D-memo.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("---\nid: D-20260105-01\nstatus: draft\nsource: memo\nsession: -\nrange: -\n"
                         "omitted: []\n---\n# 제목\n\n## 있었던 일\n메모에서 옮긴 글\n\n## 요지\n### 결정\n없음\n")
        self.assertEqual(run(["verify", path], projects=self.projects)[0], 0)
        self.assertEqual(run(["confirm", path], projects=self.projects)[0], 0)
        self.assertIn("status: active\nsource: memo", self.read(path))


class FindListTest(TempProjects):

    def setUp(self):
        TempProjects.setUp(self)
        self.copy_fixture()
        self.write_session([
            human(1, "다른 폴더의 세션에서 한 말.\n줄이 바뀌어도   찾는다."),
            agent(2, [{"type": "text", "text": "에이전트만 한 말"}]),
        ])

    def test_find_gives_session_and_uuid(self):
        code, out, err = run(["find", "--text", "제목 아래 간격도"], projects=self.projects)
        self.assertEqual(code, 0, err)
        rows = [row.split("\t") for row in out.strip().split("\n")]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][:3], [SID, uid(27), "2026-01-05 10:21"])

    def test_find_looks_in_every_folder(self):
        code, out, _ = run(["find", "--text", "한 말. 줄이 바뀌어도 찾는다"], projects=self.projects)
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith(SID2 + "\t" + uid(1) + "\t"))

    def test_find_sees_text_typed_while_agent_was_working(self):
        code, out, _ = run(["find", "--text", "제목은 굵게"], projects=self.projects)
        self.assertEqual(code, 0)
        self.assertIn(uid(29), out)

    def test_find_ignores_inserted_text_and_agent_text(self):
        for text in ("REMINDER_MARKER", "NOTIFICATION_MARKER", "SDK_MARKER", "에이전트만 한 말", "화면 파일을 보겠습니다"):
            self.assertEqual(run(["find", "--text", text], projects=self.projects)[0], 2, text)

    def test_find_with_date(self):
        self.assertEqual(run(["find", "--text", "간격", "--date", "2026-01-06"], projects=self.projects)[1].count("\n"), 1)
        self.assertEqual(run(["find", "--text", "간격", "--date", "2026-01-07"], projects=self.projects)[0], 2)
        self.assertEqual(run(["find", "--text", "간격", "--date", "어제"], projects=self.projects)[0], 1)

    def test_list_columns(self):
        code, out, err = run(["list", "--session", SID], projects=self.projects)
        self.assertEqual(code, 0, err)
        rows = [row.split("\t") for row in out.strip().split("\n")]
        self.assertTrue(all(len(row) == 5 for row in rows))
        self.assertEqual(rows[0], ["3", "01-05 10:00", "사용자", "목록 화면의 줄 간격을 넓혀 줘. 지금은 너무 좁아.", uid(1)])
        self.assertEqual([row[2] for row in rows[:3]], ["사용자", "에이전트", "도구"])
        self.assertIn(["13", "01-05 10:02", "도구", "Bash: 화면 시험을 돌린다", uid(11)], rows)
        self.assertNotIn("MARKER", out)

    def test_list_around(self):
        code, out, _ = run(["list", "--session", SID, "--around", "10:22", "--window", "2"], projects=self.projects)
        self.assertEqual(code, 0)
        self.assertEqual([row.split("\t")[4] for row in out.strip().split("\n")],
                         [uid(27), uid(28), uid(29), uid(31), uid(32), uid(33)])
        code, out, _ = run(["list", "--session", SID, "--around", "09:10"], projects=self.projects)
        self.assertEqual([row.split("\t")[4] for row in out.strip().split("\n")], [uid(44), uid(45)])
        self.assertEqual(run(["list", "--session", SID, "--around", "25:00"], projects=self.projects)[0], 1)

    def test_list_cuts_preview_at_80(self):
        self.write_session([human(1, "가" * 500)])
        out = run(["list", "--session", SID2], projects=self.projects)[1]
        self.assertEqual(out.split("\t")[3], "가" * 80)

    def test_list_unknown_session(self):
        self.assertEqual(run(["list", "--session", "없는-세션"], projects=self.projects)[0], 2)


class PendingTest(TempProjects):
    """지식 베이스도 지어낸 것이다. 메모 줄과 기록의 내용은 세지 않고 수만 센다."""

    MEMO = "%s | context | 지어낸 작업 | 지어낸 내용. 사용자 말 없음 | - | session:-"

    def setUp(self):
        TempProjects.setUp(self)
        self.kb = os.path.join(self.tmp, "kb")
        for folder in ("journal", "cases", "decisions", "context"):
            os.makedirs(os.path.join(self.kb, "raw", folder))

    def journal(self, name, lines):
        with open(os.path.join(self.kb, "raw", "journal", name), "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def record(self, folder, name, status, body=""):
        with open(os.path.join(self.kb, "raw", folder, name), "w", encoding="utf-8") as handle:
            handle.write("---\nid: %s\nstatus: %s\nsource: memo\n---\n# 제목\n%s" % (name[:13], status, body))

    def pending(self):
        code, out, err = run(["pending", self.kb], projects=self.projects)
        self.assertEqual(code, 0, err)
        return [row.split("\t") for row in out.strip().split("\n")]

    def test_nothing_pending(self):
        self.journal("2026-01-05.md", [self.MEMO % "10:00", "정리됨: X-20260105-01"])
        self.record("context", "X-20260105-01-fake.md", "active")
        self.assertEqual(self.pending(), [["합계", "메모 0", "draft 0"]])

    def test_file_without_done_line_counts_every_line(self):
        self.journal("2026-01-05.md", [self.MEMO % "10:00", "", self.MEMO % "11:00"])
        self.assertEqual(self.pending(), [["메모", "raw/journal/2026-01-05.md", "2"], ["합계", "메모 2", "draft 0"]])

    def test_only_lines_after_last_done_line_count(self):
        self.journal("2026-01-05.md", [
            self.MEMO % "10:00", "정리됨: X-20260105-01",
            self.MEMO % "11:00", self.MEMO % "12:00", "정리됨: 없음",
            self.MEMO % "13:00"])
        self.journal("2026-01-06.md", [self.MEMO % "09:00", "정리됨: 없음"])
        self.assertEqual(self.pending(), [["메모", "raw/journal/2026-01-05.md", "1"], ["합계", "메모 1", "draft 0"]])

    def test_draft_records_are_counted_by_header_only(self):
        self.record("cases", "C-20260105-01-fake.md", "draft")
        self.record("decisions", "D-20260105-01-fake.md", "active", "status: draft 라는 글자가 본문에 있다\n")
        self.record("context", "X-20260105-02-fake.md", "superseded")
        self.assertEqual(self.pending(), [["draft", "raw/cases/C-20260105-01-fake.md"], ["합계", "메모 0", "draft 1"]])

    def test_folder_that_is_not_a_knowledge_base(self):
        self.assertEqual(run(["pending", self.tmp], projects=self.projects)[0], 1)


if __name__ == "__main__":
    unittest.main()
