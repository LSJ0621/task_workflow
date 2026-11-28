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
        self.assertIn("규칙 저장소를 못 찾았다", done.stderr.decode("utf-8"))
        self.assertIn("플러그인 저장소를 못 찾았다", done.stderr.decode("utf-8"))
        self.assertEqual((last["cases"], last["memo_lines"]), (2, 2))
        self.assertEqual(self.table_rows()[0][1:], ["0", "2", "-", "0", "-", "-", "-", "-", "-", "-", "-", "-", "-", "2"])

    # -- 설치본에서 돌릴 때 -------------------------------------------------

    def installed_copy(self):
        """Claude 설정 저장소 안의 추적되지 않는 폴더에 플러그인을 설치한 모양을 만든다. (설정 저장소, 설치본의 measure.py)"""
        config = os.path.join(self.tmp, "config")
        root = os.path.join(config, "plugins", "cache", "market", "fake-plugin", "0.1.0")
        scripts = os.path.join(root, "skills", "analyze-context", "scripts")
        os.makedirs(scripts)
        os.makedirs(os.path.join(root, "skills", "write-records", "scripts"))
        shutil.copy(SCRIPT, scripts)
        shutil.copy(os.path.join(os.path.dirname(HERE), "..", "..", "write-records", "scripts", "session_extract.py"),
                    os.path.join(root, "skills", "write-records", "scripts"))
        self.write(root, ".claude-plugin/plugin.json", '{"name": "fake-plugin"}')
        self.write(root, "skills/analyze-context/SKILL.md", "사" * 70)
        self.write(root, "README.md", "아" * 35)
        self.git(config, "init", "-q", "-b", "main")
        self.write(config, ".gitignore", "plugins/\n")
        self.commit(config, "2026-01-02", "설정 저장소", {"CLAUDE.md": "가" * 100})
        return config, os.path.join(scripts, "measure.py")

    def run_installed(self, script, config, *args, env=None):
        full = dict(os.environ, TZ="Asia/Seoul", CLAUDE_CONFIG_DIR=config)
        for name in ("KNOWLEDGE_BASE_DIR", "RULE_CHANGE_LIMITS", "PLUGIN_REPO_DIR"):
            full.pop(name, None)
        full.update(env or {})
        done = subprocess.run([sys.executable, script, self.kb, "--today", TODAY, "--json", "--no-write",
                               "--projects-dir", self.projects] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=full)
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8"))
        return json.loads(done.stdout.decode("utf-8"))["weeks"], done.stderr.decode("utf-8")

    def test_installed_copy_does_not_take_the_config_repository_for_the_plugin_repository(self):
        config, script = self.installed_copy()
        (last, this), err = self.run_installed(script, config)
        self.assertIn("플러그인 저장소를 못 찾았다", err)
        # 설정 저장소의 md(CLAUDE.md 100자)를 플러그인 md로 세지 않는다. 이번 주만 설치본 폴더(70자 + 35자)에서 센다
        self.assertEqual((last["plugin_md_chars"], this["plugin_md_chars"]), (None, 105))
        self.assertEqual((last["evolve_commits"], last["evolve_shrinking"], this["evolve_commits"]), (None, None, None))
        self.assertEqual(last["rule_chars"], {"CLAUDE.md": 100})
        self.assertEqual(last["messages"], 5)

    def test_installed_copy_finds_the_plugin_repository_from_the_project_card(self):
        config, script = self.installed_copy()
        self.write(self.kb, "wiki/projects/fake-plugin.md", "# fake-plugin\n\n- 저장소: `%s` (GitHub `fake/plugin`)\n" % self.plugin)
        (last, this), err = self.run_installed(script, config, "--rules-repo", self.rules)
        self.assertNotIn("못 찾았다", err)
        self.assertEqual((last["plugin_md_chars"], this["plugin_md_chars"]), (390, 450))
        self.assertEqual((last["evolve_commits"], last["evolve_shrinking"]), (3, 1))

    def test_installed_copy_takes_the_plugin_repository_from_environment_or_argument(self):
        config, script = self.installed_copy()
        (last, _), err = self.run_installed(script, config, "--rules-repo", self.rules, env={"PLUGIN_REPO_DIR": self.plugin})
        self.assertEqual((last["plugin_md_chars"], last["evolve_commits"]), (390, 3))
        self.assertNotIn("못 찾았다", err)
        other = os.path.join(self.tmp, "other-plugin")
        os.makedirs(other)
        self.git(other, "init", "-q", "-b", "main")
        self.commit(other, "2026-01-02", "다른 저장소", {"README.md": "자" * 11})
        (last, _), _ = self.run_installed(script, config, "--rules-repo", self.rules, "--plugin-repo", other,
                                          env={"PLUGIN_REPO_DIR": self.plugin})
        self.assertEqual(last["plugin_md_chars"], 11)   # 인자가 환경 변수보다 먼저다

    def test_checkout_copy_uses_its_own_repository(self):
        # 이 시험 파일이 든 저장소(플러그인 저장소의 체크아웃)에서는 인자 없이도 그 저장소를 찾는다
        full = dict(os.environ, TZ="Asia/Seoul", CLAUDE_CONFIG_DIR=os.path.join(self.tmp, "없는-설정"))
        for name in ("KNOWLEDGE_BASE_DIR", "RULE_CHANGE_LIMITS", "PLUGIN_REPO_DIR"):
            full.pop(name, None)
        done = subprocess.run([sys.executable, SCRIPT, self.kb, "--today", TODAY, "--json", "--no-write",
                               "--projects-dir", self.projects], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=full)
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8"))
        err = done.stderr.decode("utf-8")
        self.assertNotIn("플러그인 저장소를 못 찾았다", err)
        self.assertIn("규칙 저장소를 못 찾았다", err)

    def test_who_decided_is_read_from_a_line_that_starts_with_it(self):
        told = '설명에 "누가 정했는지: 자가 발전"이라는 말이 나오는 사용자 커밋\n\n' + USER
        self.commit(self.rules, "2026-01-10", told, {"CLAUDE.md": "가" * 120})
        self.commit(self.rules, "2026-01-11", "줄 앞에 공백이 있는 자가 발전 커밋\n\n  " + EVOLVE + ".", {"CLAUDE.md": "가" * 110})
        last = self.weeks("--no-write")[0]
        self.assertEqual((last["evolve_commits"], last["evolve_shrinking"]), (4, 2))

    # -- 쓰임 표 -----------------------------------------------------------

    def skill_calls(self, number, day, calls):
        """Skill 도구 호출만 든 에이전트 줄. calls 는 [(호출 id, 스킬 이름)]"""
        blocks = [{"type": "tool_use", "id": call, "name": "Skill", "input": {"skill": name}} for call, name in calls]
        return {"type": "assistant", "uuid": uid(number), "timestamp": "%sT03:00:30.000Z" % day, "cwd": "/fake/app",
                "isSidechain": False, "message": {"role": "assistant", "model": "claude-fake-1", "content": blocks}}

    def build_usage(self):
        sid = "bbbbbbbb-0000-4000-8000-000000000001"
        first = self.skill_calls(101, "2026-01-06", [("call-1", "fake-plugin:analyze-context"), ("call-2", "other:helper")])
        self.session(sid, [first, self.skill_calls(102, "2026-01-07", [("call-3", "other:helper")]),
                           self.skill_calls(103, "2026-01-13", [("call-4", "other:helper")])])
        self.session(sid, [self.skill_calls(104, "2026-01-08", [("call-5", "other:inner")])], sub="agent-y")   # 서브에이전트가 부른 것
        self.session("bbbbbbbb-0000-4000-8000-000000000002", [first])                                        # 이어 연 세션에 복사된 호출
        self.session("bbbbbbbb-0000-4000-8000-000000000003", [                                               # 예약 작업 세션은 따로 센다
            {"type": "user", "uuid": uid(111), "timestamp": "2026-01-08T20:09:00.000Z", "turnOrigin": "scheduled",
             "promptSource": "system", "message": {"role": "user", "content": "<scheduled-task name=\"daily\">지시문</scheduled-task>"}},
            self.skill_calls(112, "2026-01-08", [("call-6", "other:helper")])])
        head = "# 모은 말\n\n| 시각 | 세션 | 종류 | 사용자 말 | 메모·기록 |\n| :- | :- | :- | :- | :- |\n"
        row = "| %s | bbbbbbbb-0000-4000-8000-000000000001 | %s | 지어낸 말 | %s |\n"
        self.write(self.kb, "evolve/signals/2026-01-06.md", head + row % ("10:00", "다시 물음", "없음") + row % ("10:05", "다시 물음", "메모 10:06")
                   + row % ("10:10", "지적", "없음") + row % ("10:20", "지적", "메모 10:21") + row % ("10:30", "만족", "없음"))
        self.write(self.kb, "evolve/signals/2026-01-08.md", head + row % ("09:00", "지적", "없음") + row % ("09:30", "지적", "C-20260107-01"))
        self.write(self.kb, "evolve/signals/2026-01-09.md", head)                       # 실을 것이 없던 날
        self.write(self.kb, "evolve/signals/2025-12-30.md", head + row % ("09:00", "다시 물음", "없음"))   # 재는 주 밖
        board = "# 상황판\n\n## 가\n- 어디까지: 지어낸 일\n- 고친 날짜: %s\n\n## 나\n- 고친 날짜: %s\n\n## 다\n- 고친 날짜: %s\n\n## 라\n- 어디까지: 날짜 없음\n"
        self.git(self.kb, "init", "-q", "-b", "main")
        # 지난주 끝(01-11)에 커밋되어 있던 상황판: 가(22일 전)와 나(17일 전)가 오래됐다. 다(14일 전)는 넘지 않았다
        self.commit(self.kb, "2026-01-10", "상황판", {"wiki/board.md": board % ("2025-12-20", "2025-12-25", "2025-12-28")})
        # 지금(01-14) 파일: 가(25일 전)만 오래됐다. 다(14일 전)는 넘지 않았다
        self.write(self.kb, "wiki/board.md", board % ("2025-12-20", "2026-01-13", "2025-12-31"))

    def usage(self, *args):
        code, out, err = self.measure("--json", *args)
        self.assertEqual(code, 0, err)
        return json.loads(out)["usage"]

    def test_usage_of_last_week_and_this_week(self):
        self.build_usage()
        last, this = self.usage()
        unused_last, unused_this = last.pop("skills_unused"), this.pop("skills_unused")   # 이 플러그인의 스킬 목록은 아래 설치본 시험에서 본다
        self.assertEqual(last, {
            "week": "2026-01-05", "last_day": "2026-01-11",
            "reasks": 2, "bare_corrections": 2, "collected_days": 3,
            "stale_board": 2,
            "skill_runs": {"fake-plugin:analyze-context": 1, "other:helper": 2, "other:inner": 1},
            "skill_runs_scheduled": {"other:helper": 1},     # 예약 작업 세션에서 부른 것은 대화 세션의 횟수에 넣지 않는다
        })
        self.assertEqual(this, {
            "week": "2026-01-12", "last_day": "2026-01-14",
            "reasks": None, "bare_corrections": None, "collected_days": 0,
            "stale_board": 1,
            "skill_runs": {"other:helper": 1},
            "skill_runs_scheduled": {},
        })
        self.assertEqual(unused_last, unused_this)

    def test_usage_table_is_a_separate_file_and_metrics_table_is_unchanged(self):
        before = self.weeks("--no-write")
        self.build_usage()
        self.write(self.kb, "evolve/usage.md", "\n".join([
            "# 쓰임", "", "| 주 | 다시 물음 |", "| :- | -: |",
            "| 2025-12-22 ~ 12-28 | 4 | 예전 줄 |", "| 2026-01-05 ~ 01-09 | 999 | 덮어쓸 줄 |", ""]))
        code, out, err = self.measure()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.weeks("--no-write"), before)                               # 있던 숫자는 그대로다
        self.assertEqual(len(self.table_rows()), 2)                                      # 측정값 표에는 줄이 더 붙지 않는다
        with open(os.path.join(self.kb, "evolve", "metrics.md"), encoding="utf-8") as handle:
            self.assertNotIn("쓰임", handle.read().split("## 세는 방법")[0])
        with open(os.path.join(self.kb, "evolve", "usage.md"), encoding="utf-8") as handle:
            text = handle.read()
        rows = [[c.strip() for c in line.strip("|").split("|")] for line in text.splitlines() if line.startswith("| 2")]
        self.assertEqual([row[0] for row in rows], ["2025-12-22 ~ 12-28", "2026-01-05 ~ 01-11", "2026-01-12 ~ 01-14"])
        self.assertEqual(rows[0][1:], ["4", "예전 줄"])
        self.assertEqual(rows[1][1:5], ["2", "2", "3", "2"])
        self.assertTrue(rows[1][5].startswith("other:helper 2, fake-plugin:analyze-context 1, other:inner 1"), rows[1][5])
        self.assertEqual(rows[1][6], "other:helper 1")                                  # 예약 작업이 쓴 스킬은 칸이 따로다
        self.assertEqual(rows[2][1:5], ["-", "-", "0", "1"])
        self.assertEqual((rows[2][5], rows[2][6]), ("other:helper 1", "없음"))
        self.assertIn("| 스킬 실행 | 예약 작업이 쓴 스킬 | 안 불림 |", text)
        self.assertIn("| 주 | 다시 물음 | 메모 없는 지적 | 모은 날 | 오래된 상황판 묶음 | 스킬 실행 |", text)
        self.assertIn("고침: " + os.path.join(self.kb, "evolve", "usage.md"), out)
        self.measure()                                                                   # 다시 돌려도 같은 파일이다
        with open(os.path.join(self.kb, "evolve", "usage.md"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), text)

    def test_usage_without_lists_board_or_calls(self):
        last, this = self.usage("--no-write")
        for row in (last, this):
            self.assertEqual((row["reasks"], row["bare_corrections"], row["collected_days"], row["skill_runs"]), (None, None, 0, {}))
            self.assertEqual(row["skill_runs_scheduled"], {})
        self.assertEqual((last["stale_board"], this["stale_board"]), (None, None))       # 상황판 파일도 지식 베이스 저장소도 없다
        self.assertFalse(os.path.exists(os.path.join(self.kb, "evolve", "usage.md")))

    def test_usage_lists_unused_skills_of_the_plugin_the_script_is_in(self):
        config, script = self.installed_copy()
        self.build_usage()
        done = subprocess.run([sys.executable, script, self.kb, "--today", TODAY, "--json", "--no-write",
                               "--projects-dir", self.projects],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ, TZ="Asia/Seoul", CLAUDE_CONFIG_DIR=config))
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8"))
        last, this = json.loads(done.stdout.decode("utf-8"))["usage"]
        self.assertEqual(last["skills_unused"], [])                                      # 지난주에는 불렸다
        self.assertEqual(this["skills_unused"], ["fake-plugin:analyze-context"])

    def test_usage_counts_skills_a_scheduled_session_ran_through_instruction_files(self):
        config, script = self.installed_copy()
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script))))

        def read(number, day, path):
            return {"type": "assistant", "uuid": uid(number), "timestamp": "%sT03:00:30.000Z" % day, "isSidechain": False,
                    "message": {"role": "assistant", "model": "claude-fake-1",
                                "content": [{"type": "tool_use", "id": "read-%d" % number, "name": "Read", "input": {"file_path": path}}]}}

        def scheduled(number, day):
            return {"type": "user", "uuid": uid(number), "timestamp": "%sT03:00:00.000Z" % day, "turnOrigin": "scheduled",
                    "promptSource": "system", "message": {"role": "user", "content": "<scheduled-task name=\"daily\">지시문</scheduled-task>"}}
        first, second, talk = ("cccccccc-0000-4000-8000-00000000000%d" % n for n in (1, 2, 3))
        # 지난주 예약 작업 두 번: 서브에이전트가 지침 파일을 읽었다. 한 세션에서 여러 번 읽어도 한 번이다
        self.session(first, [scheduled(201, "2026-01-06"), self.skill_calls(202, "2026-01-06", [("call-s1", "fake-plugin:daily")])])
        self.session(first, [read(203, "2026-01-06", root + "/skills/analyze-context/SKILL.md"),
                             read(204, "2026-01-06", root + "/skills/analyze-context/references/judging.md"),
                             read(205, "2026-01-06", root + "/skills/no-such-skill/SKILL.md"),
                             read(206, "2026-01-06", root + "/skills/analyze-context/scripts/measure.py")], sub="agent-s1")
        self.session(second, [scheduled(211, "2026-01-07")])
        self.session(second, [read(212, "2026-01-07", root + "/skills/analyze-context/references/judging.md")], sub="agent-s2")
        # 이번 주: 대화 세션이 같은 파일을 읽은 것은 예약 작업의 쓰임이 아니다
        self.session(talk, [read(221, "2026-01-13", root + "/skills/analyze-context/SKILL.md")])
        done = subprocess.run([sys.executable, script, self.kb, "--today", TODAY, "--json", "--no-write",
                               "--projects-dir", self.projects],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ, TZ="Asia/Seoul", CLAUDE_CONFIG_DIR=config))
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8"))
        last, this = json.loads(done.stdout.decode("utf-8"))["usage"]
        self.assertEqual(last["skill_runs_scheduled"], {"fake-plugin:analyze-context": 2, "fake-plugin:daily": 1})
        self.assertEqual((last["skill_runs"], last["skills_unused"]), ({}, []))          # 예약 작업만 쓴 스킬은 안 불림이 아니다
        self.assertEqual((this["skill_runs_scheduled"], this["skills_unused"]), ({}, ["fake-plugin:analyze-context"]))

    def test_errors(self):
        self.assertEqual(self.measure(kb=self.tmp)[0], 1)
        self.assertEqual(self.measure("--weeks", "0")[0], 1)
        self.assertEqual(self.measure("--today", "어제")[0], 1)


if __name__ == "__main__":
    unittest.main()
