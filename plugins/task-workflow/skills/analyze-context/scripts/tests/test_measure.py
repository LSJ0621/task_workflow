"""measure.py 시험. 세션 기록, 지식 베이스, 저장소는 전부 임시 폴더에 지어낸 것이다.
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
SCRIPT = os.path.join(os.path.dirname(HERE), "measure.py")
EVOLVE = "누가 정했는지: 자가 발전"
USER = "누가 정했는지: 사용자"
TODAY = "2026-01-14"   # 수요일. 이번 주는 2026-01-12(월)에 시작하고 지난주는 2026-01-05(월)에 시작한다


def uid(number):
    return "00000000-0000-4000-8000-%012d" % number


def human(number, day, text="지어낸 말", cwd="/fake/app", hour=3):
    # 03:00Z 는 서울에서 같은 날 12:00 이다
    return {"type": "user", "uuid": uid(number), "timestamp": "%sT%02d:00:00.000Z" % (day, hour), "cwd": cwd,
            "isSidechain": False, "origin": {"kind": "human"}, "turnOrigin": "human", "promptSource": "typed",
            "message": {"role": "user", "content": text}}


def tools(number, day, calls, cwd="/fake/app", hour=3):
    blocks = [{"type": "tool_use", "id": "t%d" % i, "name": name, "input": params} for i, (name, params) in enumerate(calls)]
    return {"type": "assistant", "uuid": uid(number), "timestamp": "%sT%02d:00:30.000Z" % (day, hour), "cwd": cwd,
            "isSidechain": False, "message": {"role": "assistant", "model": "claude-fake-1", "content": blocks}}


def result(number, day):
    return {"type": "user", "uuid": uid(number), "timestamp": "%sT03:00:40.000Z" % day, "isSidechain": False,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t0", "content": "결과"}]}}


def edits(count):
    return [("Edit", {"file_path": "/fake/app/a.txt"})] * count


class MeasureTest(unittest.TestCase):

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="measure-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.kb = os.path.join(self.tmp, "kb")
        self.projects = os.path.join(self.tmp, "projects")
        self.rules = os.path.join(self.tmp, "rules")
        self.plugin = os.path.join(self.tmp, "plugin-repo")
        for folder in ("raw/journal", "raw/cases", "wiki/projects"):
            os.makedirs(os.path.join(self.kb, folder))
        os.makedirs(self.projects)
        self.build_knowledge_base()
        self.build_sessions()
        self.build_repos()

    # -- 지어내기 ---------------------------------------------------------

    def write(self, root, rel, text):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def session(self, sid, rows, folder="-fake-app", sub=None):
        target = os.path.join(self.projects, folder) if sub is None else os.path.join(self.projects, folder, sid, "subagents")
        os.makedirs(target, exist_ok=True)
        with open(os.path.join(target, (sub or sid) + ".jsonl"), "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def case(self, rid, day, tags="[report]"):
        self.write(self.kb, "raw/cases/%s-fake.md" % rid,
                   "---\nid: %s\ntype: case\ndate: %s\nscope: me\nstatus: active\ntags: %s\n---\n# 사례\n" % (rid, day, tags))

    def build_knowledge_base(self):
        self.case("C-20260105-01", "2026-01-05")
        self.case("C-20260107-01", "2026-01-07")
        self.case("C-20260111-01", "2026-01-11", "[notfound]")      # 못 찾음은 지적이 아니다
        self.case("C-20260112-01", "2026-01-12")
        self.case("C-20251230-01", "2025-12-30")                    # 재는 주 밖
        memo = "%s | feedback | 지어낸 작업 | 지어낸 내용 | - | session:-"
        self.write(self.kb, "raw/journal/2026-01-06.md", "\n".join([memo % "10:00", memo % "11:30", "정리됨: C-20260105-01", ""]))
        self.write(self.kb, "raw/journal/2026-01-13.md", "\n".join([memo % "9:05", "", "메모가 아닌 줄", ""]))
        self.write(self.kb, "raw/journal/2025-12-30.md", memo % "10:00")

    def build_sessions(self):
        kb = self.kb
        # 지난주 작업 세션 1: 색인과 카드를 읽었다. 도구 12번
        self.session("aaaaaaaa-0000-4000-8000-000000000001", [
            human(1, "2026-01-05"), tools(2, "2026-01-05", [("Read", {"file_path": kb + "/INDEX.md"})] + edits(9)),
            result(3, "2026-01-05"), human(4, "2026-01-05", "<system-reminder>끼워 넣은 글</system-reminder>\n둘째 말"),
            tools(5, "2026-01-05", [("Bash", {"command": "cd %s && cat wiki/projects/app.md | head" % kb}), ("Edit", {})]),
            human(6, "2026-01-13", "이번 주에 이어서 한 말"),
        ])
        # 지난주 작업 세션 2: 지식 베이스를 읽지 않았다. 도구는 서브에이전트 것까지 합쳐 10번
        self.session("aaaaaaaa-0000-4000-8000-000000000002", [
            human(11, "2026-01-07"), tools(12, "2026-01-07", edits(4)),
            tools(13, "2026-01-07", [("Bash", {"command": "echo hi > %s/raw/journal/2026-01-07.md" % kb})]),
            {"type": "user", "uuid": uid(14), "timestamp": "2026-01-07T04:00:00.000Z", "isSidechain": True,
             "origin": {"kind": "human"}, "message": {"role": "user", "content": "서브에이전트 안쪽 말"}},
        ])
        self.session("aaaaaaaa-0000-4000-8000-000000000002", [tools(15, "2026-01-07", edits(5))], sub="agent-x")
        # 지난주 세션 3: 도구가 3번뿐이라 작업 세션이 아니다. 메시지는 센다
        self.session("aaaaaaaa-0000-4000-8000-000000000003", [human(21, "2026-01-08"), tools(22, "2026-01-08", edits(3))])
        # 지난주 예약 작업 세션: 통째로 뺀다
        self.session("aaaaaaaa-0000-4000-8000-000000000004", [
            {"type": "user", "uuid": uid(31), "timestamp": "2026-01-08T20:09:00.000Z", "cwd": "/fake/app",
             "origin": {"kind": "task-notification", "subkind": "scheduled-trigger"}, "turnOrigin": "scheduled",
             "promptSource": "system", "message": {"role": "user", "content": "<scheduled-task name=\"daily\">지시문</scheduled-task>"}},
            human(32, "2026-01-08", "예약 작업 세션에 친 말"),
            tools(33, "2026-01-08", [("Read", {"file_path": kb + "/INDEX.md"})] + edits(20)),
        ])
        # 지난주 지식 베이스 폴더에서 연 세션: 작업 세션이 아니다. 메시지는 센다
        self.session("aaaaaaaa-0000-4000-8000-000000000005", [
            human(41, "2026-01-09", cwd=kb), tools(42, "2026-01-09", [("Read", {"file_path": kb + "/INDEX.md"})] + edits(11), cwd=kb),
        ], folder="-fake-kb")
        # 이번 주 작업 세션: 요약과 원본을 읽었다. 앞 세션을 이어 열어 같은 줄(1번)이 복사되어 있다
        self.session("aaaaaaaa-0000-4000-8000-000000000006", [
            human(51, "2026-01-12"), human(1, "2026-01-05"),
            tools(52, "2026-01-12", [("Grep", {"pattern": "x", "path": kb + "/raw/decisions"}),
                                     ("Bash", {"command": "grep -n 보고 \"$KNOWLEDGE_BASE_DIR/wiki/context.md\""})] + edits(8)),
            {"type": "attachment", "uuid": uid(53), "timestamp": "2026-01-12T05:00:00.000Z",
             "attachment": {"type": "queued_command", "origin": {"kind": "human"}, "prompt": "일하는 중에 친 말"}},
            {"type": "brand-new-line", "uuid": uid(54)},
        ])
        # 재는 주보다 앞에 시작한 세션의 지난 메시지는 세지 않는다
        self.session("aaaaaaaa-0000-4000-8000-000000000007", [human(61, "2025-12-29"), tools(62, "2025-12-29", edits(15))])

    def git(self, repo, *args, date="2026-01-01T12:00:00+09:00"):
        env = dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date, GIT_AUTHOR_NAME="t",
                   GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        subprocess.run(["git", "-C", repo] + list(args), check=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def commit(self, repo, date, message, files):
        for rel, text in files.items():
            self.write(repo, rel, text)
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", message, date=date + "T12:00:00+09:00")

    def build_repos(self):
        for repo in (self.rules, self.plugin):
            os.makedirs(repo)
            self.git(repo, "init", "-q", "-b", "main")
        self.commit(self.rules, "2026-01-02", "처음", {"CLAUDE.md": "가" * 100, "output-styles/style.md": "나" * 200,
                                                     "evolve/state.md": "상태"})
        self.commit(self.rules, "2026-01-06", "전역 지침을 늘린다\n\n" + EVOLVE, {"CLAUDE.md": "가" * 130})
        self.commit(self.rules, "2026-01-07", "응답 양식을 줄인다\n\n" + EVOLVE, {"output-styles/style.md": "나" * 180})
        self.commit(self.rules, "2026-01-08", "사용자가 늘린다\n\n" + USER, {"CLAUDE.md": "가" * 150})
        self.commit(self.rules, "2026-01-09", "자가 발전 상태\n\n" + EVOLVE, {"evolve/state.md": "상태 2"})
        self.commit(self.rules, "2026-01-13", "전역 지침을 줄인다\n\n누가 정했나: 자가 발전", {"CLAUDE.md": "가" * 140})
        self.commit(self.plugin, "2026-01-02", "처음", {
            "plugins/fake/.claude-plugin/plugin.json": '{"name": "fake"}',
            "plugins/fake/skills/a/SKILL.md": "다" * 300, "plugins/fake/README.md": "라" * 50, "README.md": "마" * 999})
        self.commit(self.plugin, "2026-01-07", "스킬을 늘린다\n\n" + EVOLVE, {"plugins/fake/skills/a/SKILL.md": "다" * 340})
        self.commit(self.plugin, "2026-01-08", "저장소 README\n\n" + EVOLVE, {"README.md": "마" * 10})
        self.commit(self.plugin, "2026-01-13", "스킬 문서를 더한다", {"plugins/fake/skills/b/SKILL.md": "바" * 60})

    # -- 돌리기 -----------------------------------------------------------

    def measure(self, *args, kb=None):
        env = dict(os.environ, TZ="Asia/Seoul", KNOWLEDGE_BASE_DIR="/fake/kb-from-env")
        for name in ("RULE_CHANGE_LIMITS", "CLAUDE_CONFIG_DIR"):
            env.pop(name, None)
        done = subprocess.run(
            [sys.executable, SCRIPT, kb or self.kb, "--today", TODAY, "--projects-dir", self.projects,
             "--rules-repo", self.rules, "--plugin-repo", self.plugin,
             "--limits", os.path.join(self.tmp, "없는-한도.json")] + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")

    def weeks(self, *args):
        code, out, err = self.measure("--json", *args)
        self.assertEqual(code, 0, err)
        return json.loads(out)["weeks"]

    def table_rows(self):
        with open(os.path.join(self.kb, "evolve", "metrics.md"), encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        return [[c.strip() for c in line.strip("|").split("|")] for line in lines if line.startswith("| 2")]

    # -- 시험 -------------------------------------------------------------

    def test_numbers_of_last_week_and_this_week(self):
        last, this = self.weeks()
        self.assertEqual(last, {
            "week": "2026-01-05", "last_day": "2026-01-11",
            "messages": 5,              # 세션 1의 두 마디, 세션 2·3·5의 한 마디씩. 예약 작업과 서브에이전트 안쪽은 뺀다
            "cases": 2, "cases_per_100": 40.0,
            "work_sessions": 2,
            "read_index": 50, "read_summary": 0, "read_card": 50, "read_raw": 0,
            "rule_chars": {"CLAUDE.md": 150, "output-styles/style.md": 180},
            "plugin_md_chars": 390,     # 플러그인 폴더의 md만. 저장소 맨 위 README는 뺀다
            "evolve_commits": 3, "evolve_shrinking": 1,
            "memo_lines": 2,
        })
        self.assertEqual(this, {
            "week": "2026-01-12", "last_day": "2026-01-14",
            "messages": 3,              # 이어 연 세션에 복사된 줄은 다시 세지 않는다. 일하는 중에 친 말은 센다
            "cases": 1, "cases_per_100": 33.3,
            "work_sessions": 1,
            "read_index": 0, "read_summary": 100, "read_card": 0, "read_raw": 100,
            "rule_chars": {"CLAUDE.md": 140, "output-styles/style.md": 180},
            "plugin_md_chars": 450,
            "evolve_commits": 1, "evolve_shrinking": 1,
            "memo_lines": 1,
        })

    def test_table_is_written_and_same_week_is_overwritten(self):
        self.write(self.kb, "evolve/metrics.md", "\n".join([
            "# 측정값", "", "| 주 | 메시지 |", "| :- | -: |",
            "| 2025-12-22 ~ 12-28 | 7 | 예전 줄 |", "| 2026-01-05 ~ 01-09 | 999 | 덮어쓸 줄 |", ""]))
        code, out, err = self.measure()
        self.assertEqual(code, 0, err)
        rows = self.table_rows()
        self.assertEqual([row[0] for row in rows], ["2025-12-22 ~ 12-28", "2026-01-05 ~ 01-11", "2026-01-12 ~ 01-14"])
        self.assertEqual(rows[0][1:], ["7", "예전 줄"])
        self.assertEqual(rows[1][1:], ["5", "2", "40.0", "2", "50%", "0%", "50%", "0%", "150", "180", "390", "3", "1", "2"])
        self.assertEqual(rows[2][1:], ["3", "1", "33.3", "1", "0%", "100%", "0%", "100%", "140", "180", "450", "1", "1", "1"])
        with open(os.path.join(self.kb, "evolve", "metrics.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn("999", text)
        self.assertIn("## 세는 방법", text)
        # 다시 돌려도 같은 파일이다
        self.measure()
        with open(os.path.join(self.kb, "evolve", "metrics.md"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), text)

    def test_more_weeks_and_no_write(self):
        rows = self.weeks("--weeks", "3", "--no-write")
        self.assertEqual([row["week"] for row in rows], ["2025-12-29", "2026-01-05", "2026-01-12"])
        self.assertEqual((rows[0]["messages"], rows[0]["cases"], rows[0]["memo_lines"], rows[0]["work_sessions"]), (1, 1, 1, 1))
        self.assertEqual(rows[0]["rule_chars"], {"CLAUDE.md": 100, "output-styles/style.md": 200})
        self.assertFalse(os.path.exists(os.path.join(self.kb, "evolve", "metrics.md")))

    def test_min_tools_changes_what_a_work_session_is(self):
        last = self.weeks("--min-tools", "3", "--no-write")[0]
        self.assertEqual((last["work_sessions"], last["read_index"]), (3, 33))

    def test_read_root_tells_which_paths_are_the_knowledge_base(self):
        last = self.weeks("--read-root", "/somewhere/else", "--no-write")[0]
        self.assertEqual((last["work_sessions"], last["read_index"], last["read_card"]), (3, 0, 0))

    def test_rule_files_can_be_given(self):
        last = self.weeks("--rule-files", "CLAUDE.md", "--no-write")[0]
        self.assertEqual(last["rule_chars"], {"CLAUDE.md": 150})
        self.assertEqual((last["evolve_commits"], last["evolve_shrinking"]), (2, 0))

    def test_values_that_cannot_be_read_are_empty(self):
        env = dict(os.environ, TZ="Asia/Seoul", CLAUDE_CONFIG_DIR=os.path.join(self.tmp, "없는-설정"))
        env.pop("KNOWLEDGE_BASE_DIR", None)
        done = subprocess.run([sys.executable, SCRIPT, self.kb, "--today", TODAY, "--json", "--plugin-repo", self.tmp],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8"))
        last = json.loads(done.stdout.decode("utf-8"))["weeks"][0]
        self.assertEqual((last["messages"], last["work_sessions"], last["read_index"]), (0, 0, None))
        self.assertEqual((last["rule_chars"], last["plugin_md_chars"], last["evolve_commits"]), (None, None, None))
        self.assertEqual((last["cases"], last["memo_lines"]), (2, 2))
        self.assertEqual(self.table_rows()[0][1:], ["0", "2", "-", "0", "-", "-", "-", "-", "-", "-", "-", "-", "-", "2"])

    def test_errors(self):
        self.assertEqual(self.measure(kb=self.tmp)[0], 1)
        self.assertEqual(self.measure("--weeks", "0")[0], 1)
        self.assertEqual(self.measure("--today", "어제")[0], 1)


if __name__ == "__main__":
    unittest.main()
