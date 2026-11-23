"""check_invariants.py 시험.

지식 베이스, 플러그인 폴더, Claude 설정 폴더는 전부 임시 폴더에 지어낸 것이다.
돌리기: python3 -m unittest discover -s <이 폴더>
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "check_invariants.py")
SID = "11111111-1111-4111-8111-111111111111"
RANGE = "aaaa0001..aaaa0002"


def record(rid, kind, status="active", scope="me", extra="", body=None, title="지어낸 기록"):
    if body is None:
        body = "## 요지\n### 결정\n지어낸 결정.\n\n### 이유\n지어낸 이유.\n" if kind == "decision" else "## 요지\n지어낸 글.\n"
    return ("---\nid: %s\ntype: %s\ntitle: %s\ndate: 2026-01-05\nscope: %s\ndomain: common\n"
            "status: %s          # draft | active | superseded | archived\n%s---\n\n# %s\n\n%s"
            % (rid, kind, title, scope, status, extra, title, body))


class Base(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="check-invariants-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.kb = os.path.join(self.tmp, "kb")
        self.plugin = os.path.join(self.tmp, "plugin")
        self.claude = os.path.join(self.tmp, "claude")
        for folder in ("raw/journal", "raw/cases", "raw/decisions", "raw/context", "wiki/projects", "evolve"):
            os.makedirs(os.path.join(self.kb, folder))
        for folder in ("skills/write-records/scripts", "skills/leave-memo", "agents", "hooks", ".claude-plugin"):
            os.makedirs(os.path.join(self.plugin, folder))
        self.write(self.plugin, ".claude-plugin/plugin.json", '{"name": "fake-plugin"}')
        self.write(self.plugin, "skills/write-records/SKILL.md", "x")
        self.write(self.plugin, "skills/write-records/scripts/session_extract.py", "x")
        self.write(self.plugin, "skills/leave-memo/SKILL.md", "x")
        self.write(self.plugin, "agents/record-checker.md", "x")
        self.write(self.plugin, "hooks/remind_answer_scope.py", "x")
        os.makedirs(os.path.join(self.claude, "scheduled-tasks", "daily-upkeep"))
        self.write(self.kb, "wiki/context.md", "# 맥락 요약\n\n## 모든 프로젝트에 걸린 결정\n- 지어낸 결정 (D-20260105-01)\n")
        self.write(self.kb, "wiki/board.md", "# 상황판\n")
        self.write(self.kb, "evolve/rule-cases.md",
                   "| 사례 | 한 줄 요약 | 관련 규칙 | 규칙과 관계 |\n| :- | :- | :- | :- |\n")
        self.write(self.kb, "raw/decisions/D-20260105-01-fake.md", record("D-20260105-01", "decision"))

    def write(self, root, rel, text):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def append(self, rel, text):
        with open(os.path.join(self.kb, rel), "a", encoding="utf-8") as handle:
            handle.write(text)

    def check(self, *options):
        done = subprocess.run(
            [sys.executable, SCRIPT, self.kb, "--plugin-dir", self.plugin, "--claude-dir", self.claude,
             "--today", "2026-02-01"] + list(options),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")

    def problems(self, *options):
        code, out, _ = self.check(*options)
        return code, [line.strip()[len("[문제] "):] for line in out.split("\n") if line.strip().startswith("[문제]")]

    def notices(self, *options):
        code, out, _ = self.check(*options)
        return code, [line.strip()[len("[알림] "):] for line in out.split("\n") if line.strip().startswith("[알림]")]


class StatusTest(Base):

    def test_clean_knowledge_base_passes(self):
        code, out, err = self.check()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(out.strip().split("\n")[-1].strip(), "통과")
        self.assertNotIn("[알림]", out)

    def test_archived_record_needs_no_summary_line(self):
        self.write(self.kb, "raw/decisions/D-20260105-02-fake.md",
                   record("D-20260105-02", "decision", "archived", extra="archived_reason: done\n"))
        self.write(self.kb, "raw/context/X-20260105-01-fake.md",
                   record("X-20260105-01", "context", "archived", extra="archived_reason: expired\n"))
        self.assertEqual(self.problems(), (0, []))

    def test_archived_record_needs_a_known_reason(self):
        self.write(self.kb, "raw/decisions/D-20260105-02-fake.md", record("D-20260105-02", "decision", "archived"))
        self.write(self.kb, "raw/decisions/D-20260105-03-fake.md",
                   record("D-20260105-03", "decision", "archived", extra="archived_reason: old\n"))
        code, found = self.problems()
        self.assertEqual(code, 1)
        self.assertEqual(len(found), 2)
        self.assertTrue(all("archived_reason" in line for line in found))

    def test_moved_reasons_need_moved_to(self):
        for number, reason in enumerate(("in-rules", "project-doc"), 2):
            self.write(self.kb, "raw/decisions/D-20260105-0%d-fake.md" % number,
                       record("D-20260105-0%d" % number, "decision", "archived", extra="archived_reason: %s\n" % reason))
        code, found = self.problems()
        self.assertEqual((code, len(found)), (1, 2))
        self.assertTrue(all("moved_to 없음" in line for line in found))
        for number, reason in enumerate(("in-rules", "project-doc"), 2):
            self.write(self.kb, "raw/decisions/D-20260105-0%d-fake.md" % number,
                       record("D-20260105-0%d" % number, "decision", "archived",
                              extra="archived_reason: %s\nmoved_to: 전역 지침 보고 절\n" % reason))
        self.assertEqual(self.problems(), (0, []))

    def test_only_active_records_may_be_in_summary_and_cards(self):
        self.write(self.kb, "raw/decisions/D-20260105-02-fake.md",
                   record("D-20260105-02", "decision", "archived", extra="archived_reason: done\n"))
        self.write(self.kb, "raw/decisions/D-20260105-03-fake.md",
                   record("D-20260105-03", "decision", "superseded", extra="superseded_by: D-20260105-01\n"))
        self.write(self.kb, "raw/cases/C-20260105-01-fake.md", record("C-20260105-01", "case", "draft"))
        self.append("wiki/context.md", "- 보관한 결정 (D-20260105-02)\n")
        self.write(self.kb, "wiki/projects/proj.md",
                   "# proj\n\n## 유효한 결정\n- 대체된 결정 (D-20260105-03)\n- 사례: C-20260105-01\n")
        code, found = self.problems("--skip-rule-cases")
        self.assertEqual(code, 1)
        self.assertEqual(sorted(found), [
            "active 가 아닌(archived) 기록이 요약(wiki/context.md, wiki/projects/)에 올라가 있음: D-20260105-02",
            "active 가 아닌(superseded) 기록이 요약(wiki/context.md, wiki/projects/)에 올라가 있음: D-20260105-03",
            "확인 전(draft) 기록이 요약(wiki/context.md, wiki/projects/)에 올라가 있음: C-20260105-01",
        ])
        # --skip-summary 는 "요약에 나와야 한다"만 건너뛴다. 올라가면 안 되는 기록은 그대로 본다
        self.assertEqual(len(self.problems("--skip-rule-cases", "--skip-summary")[1]), 3)

    def test_active_record_missing_from_summary_is_still_a_problem(self):
        self.write(self.kb, "raw/context/X-20260105-01-fake.md", record("X-20260105-01", "context"))
        code, found = self.problems()
        self.assertEqual((code, found), (1, ["요약(wiki/context.md, wiki/projects/)에 없는 유효한 기록: X-20260105-01"]))
        self.assertEqual(self.problems("--skip-summary"), (0, []))

    def test_valid_until_must_be_a_date(self):
        self.write(self.kb, "raw/context/X-20260105-01-fake.md",
                   record("X-20260105-01", "context", extra="valid_until: 다음 주\n"))
        self.append("wiki/context.md", "- 지어낸 맥락 (X-20260105-01)\n")
        code, found = self.problems()
        self.assertEqual(code, 1)
        self.assertIn("valid_until", found[0])


class FolderTest(Base):

    def test_rule_cases_table_is_read_from_evolve(self):
        self.write(self.kb, "raw/cases/C-20260105-01-fake.md", record("C-20260105-01", "case"))
        code, found = self.problems()
        self.assertEqual((code, found), (1, ["규칙별 사례표에 없는 사례: C-20260105-01"]))
        self.append("evolve/rule-cases.md", "| C-20260105-01 | 지어낸 일 | 없음 | 규칙 없음 |\n")
        self.assertEqual(self.problems(), (0, []))
        self.assertIn("규칙별 사례표 1줄", self.check()[1])

    def test_old_location_of_rule_cases_table_still_works(self):
        shutil.move(os.path.join(self.kb, "evolve", "rule-cases.md"), os.path.join(self.kb, "wiki", "rule-cases.md"))
        self.write(self.kb, "raw/cases/C-20260105-01-fake.md", record("C-20260105-01", "case"))
        self.assertEqual(self.problems(), (1, ["규칙별 사례표에 없는 사례: C-20260105-01"]))

    def test_rule_cases_table_in_both_places_is_a_problem(self):
        shutil.copy(os.path.join(self.kb, "evolve", "rule-cases.md"), os.path.join(self.kb, "wiki", "rule-cases.md"))
        code, found = self.problems()
        self.assertEqual(code, 1)
        self.assertIn("두 곳", found[0])

    def test_session_excerpts_need_no_header_and_ids_inside_are_not_checked(self):
        self.write(self.kb, "raw/sessions/%s.md" % SID,
                   "# 세션 발췌\n\n<!-- range:start %s -->\n**사용자** (10:00)\n> C-20990101-01 같은 건 없어\n<!-- range:end -->\n" % RANGE)
        self.assertEqual(self.problems(), (0, []))

    def test_ids_in_evolve_documents_are_checked(self):
        self.write(self.kb, "evolve/hypotheses.md", "## CLAUDE.md — 보고\n근거 C-20990101-01\n")
        code, found = self.problems()
        self.assertEqual((code, found), (1, ["없는 id 참조 C-20990101-01: evolve/hypotheses.md"]))


class SourceTest(Base):

    def session_record(self, inside, rid="C-20260105-01"):
        body = "## 있었던 일\n<!-- extract:start -->\n%s<!-- extract:end -->\n\n## 요지\n지어낸 글.\n" % inside
        extra = "source: session\nsession: %s\nrange: %s\nomitted: []\n" % (SID, RANGE)
        self.write(self.kb, "raw/cases/%s-fake.md" % rid, record(rid, "case", "draft", extra=extra, body=body))

    def test_old_format_session_record_passes(self):
        self.session_record("**사용자** (10:00)\n> 지어낸 말\n\n**에이전트** (10:00)\n> 지어낸 답\n")
        self.assertEqual(self.problems(), (0, []))

    def test_old_format_memo_record_passes(self):
        self.write(self.kb, "raw/context/X-20260105-01-fake.md", record(
            "X-20260105-01", "context", "superseded",
            extra="source: memo\nsession: -\nrange: -\nsuperseded_by: D-20260105-01\n", body="## 있었던 일\n메모에서 옮긴 글\n"))
        self.assertEqual(self.problems(), (0, []))

    def test_new_format_record_needs_its_excerpt_block(self):
        self.session_record("발췌: raw/sessions/%s.md %s\n\n**사용자** (10:00)\n> 지어낸 말\n" % (SID, RANGE))
        code, found = self.problems()
        self.assertEqual(code, 1)
        self.assertIn("발췌 위치의 파일이 없음", found[0])
        self.write(self.kb, "raw/sessions/%s.md" % SID,
                   "# 세션 발췌\n\n<!-- range:start aaaa0001..aaaa0009 -->\n**사용자** (10:00)\n> 지어낸 말\n<!-- range:end -->\n")
        code, found = self.problems()
        self.assertEqual(code, 1)
        self.assertIn("발췌 위치의 범위가 그 파일에 없음", found[0])
        self.append("raw/sessions/%s.md" % SID,
                    "\n<!-- range:start %s omitted:aaaa0005 -->\n**사용자** (10:00)\n> 지어낸 말\n<!-- range:end -->\n" % RANGE)
        self.assertEqual(self.problems(), (0, []))

    def test_session_record_still_needs_both_marks(self):
        body = "## 있었던 일\n<!-- extract:start -->\n**사용자** (10:00)\n> 지어낸 말\n\n## 요지\n지어낸 글.\n"
        extra = "source: session\nsession: %s\nrange: %s\n" % (SID, RANGE)
        self.write(self.kb, "raw/cases/C-20260105-01-fake.md", record("C-20260105-01", "case", "draft", extra=extra, body=body))
        code, found = self.problems()
        self.assertEqual(code, 1)
        self.assertIn("extract 표시가 하나씩이 아님", found[0])

    def test_agent_source_is_only_for_structure_decisions(self):
        body = "## 요지\n훅을 더했다.\n\n## 이유와 근거\n지어낸 근거.\n\n## 바뀐 것\n지어낸 파일.\n"
        self.write(self.kb, "raw/decisions/D-20260105-02-fake.md", record(
            "D-20260105-02", "decision", scope="project:fake", extra="source: agent\ntags: [hooks, structure]\n", body=body))
        self.append("wiki/context.md", "- 구조 결정 (D-20260105-02)\n")
        self.assertEqual(self.problems(), (0, []))
        self.write(self.kb, "raw/decisions/D-20260105-03-fake.md", record(
            "D-20260105-03", "decision", extra="source: agent\ntags: [hooks]\n"))
        self.write(self.kb, "raw/context/X-20260105-01-fake.md", record(
            "X-20260105-01", "context", extra="source: agent\ntags: [structure]\n"))
        self.append("wiki/context.md", "- (D-20260105-03) (X-20260105-01)\n")
        code, found = self.problems()
        self.assertEqual((code, len(found)), (1, 2))
        self.assertTrue(all("source: agent" in line for line in found))

    def test_unknown_source_is_a_problem(self):
        self.write(self.kb, "raw/context/X-20260105-01-fake.md", record("X-20260105-01", "context", "draft", extra="source: chat\n"))
        code, found = self.problems()
        self.assertEqual(code, 1)
        self.assertIn("source 값이", found[0])


class NoticeTest(Base):

    def test_card_line_naming_a_scheduled_task_that_does_not_exist(self):
        self.write(self.kb, "wiki/projects/proj.md", (
            "# proj\n\n## 유효한 결정\n"
            "- 정리는 예약 작업 `daily-upkeep`으로 돈다 (D-20260105-01)\n"
            "- 사서 정리는 매일 아침 예약 작업 `no-such-task`로 돈다 (D-20260105-01)\n"))
        code, found = self.notices()
        self.assertEqual(code, 0)
        self.assertEqual(found, ["실제 대조: wiki/projects/proj.md:5 예약 작업 `no-such-task` 없음"])
        out = self.check()[1]
        self.assertIn("알림 1건", out)
        self.assertEqual(out.strip().split("\n")[-1].strip(), "통과")

    def test_names_that_exist_give_no_notice(self):
        self.write(self.kb, "wiki/board.md", (
            "# 상황판\n\n## proj\n"
            "- 어디까지: 새 스킬 `write-records`와 스크립트 `session_extract.py`, 서브에이전트 `record-checker`가 생겼다. "
            "메모 스킬(`fake-plugin:leave-memo`)과 훅 `remind_answer_scope.py`, `other-plugin:whatever`, 브랜치 `feat/docker`.\n"))
        self.assertEqual(self.notices(), (0, []))

    def test_names_that_do_not_exist_in_summary_board_and_cards(self):
        self.append("wiki/context.md", "- 화면 작업 스킬(`build-screens`)을 따른다 (D-20260105-01)\n")
        self.write(self.kb, "wiki/board.md", (
            "# 상황판\n\n## proj\n- 어디까지: 서브에이전트 `evolve-report-checker`가 확인한다. `gone_script.py`를 돌린다. "
            "`fake-plugin:old-skill`도 쓴다. 훅 `old_hook`이 알린다.\n"))
        code, found = self.notices()
        self.assertEqual(code, 0)
        self.assertEqual(sorted(found), [
            "실제 대조: wiki/board.md:4 서브에이전트 `evolve-report-checker` 없음",
            "실제 대조: wiki/board.md:4 스크립트 `gone_script.py` 없음",
            "실제 대조: wiki/board.md:4 스킬 `fake-plugin:old-skill` 없음",
            "실제 대조: wiki/board.md:4 훅 `old_hook` 없음",
            "실제 대조: wiki/context.md:5 스킬 `build-screens` 없음",
        ])

    def test_kind_that_cannot_be_looked_up_is_reported_once(self):
        shutil.rmtree(os.path.join(self.claude, "scheduled-tasks"))
        self.append("wiki/context.md", "- 예약 작업 `a-task`와 예약 작업 `b-task` (D-20260105-01)\n")
        code, found = self.notices()
        self.assertEqual((code, found), (0, ["실제 대조: 예약 작업 목록을 읽을 폴더가 없어 대조하지 못함"]))

    def test_active_record_past_valid_until(self):
        for number, (status, until, reason) in enumerate((
                ("active", "2026-01-31", ""), ("active", "2026-02-01", ""), ("active", "2026-03-01", ""),
                ("archived", "2026-01-01", "archived_reason: expired\n")), 1):
            self.write(self.kb, "raw/context/X-20260105-0%d-fake.md" % number, record(
                "X-20260105-0%d" % number, "context", status, extra="valid_until: %s\n%s" % (until, reason)))
        self.append("wiki/context.md", "- (X-20260105-01) (X-20260105-02) (X-20260105-03)\n")
        code, found = self.notices()
        self.assertEqual(code, 0)
        self.assertEqual(found, ["기한 지남: X-20260105-01 valid_until 2026-01-31 (X-20260105-01-fake.md)"])

    def git(self, repo, *args, date="2026-01-20T12:00:00"):
        env = dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date,
                   GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        subprocess.run(["git", "-C", repo] + list(args), check=True, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def repo_with_commit(self, name, date):
        repo = os.path.join(self.tmp, name)
        os.makedirs(repo)
        self.git(repo, "init", "-q")
        self.write(repo, "a.txt", "x")
        self.git(repo, "add", "a.txt")
        self.git(repo, "commit", "-q", "-m", "c", date=date)
        return repo

    def board(self, name, day):
        self.append("wiki/board.md", "\n## %s\n- 어디까지: 지어낸 일\n- 고친 날짜: %s\n" % (name, day))

    def test_board_date_older_than_last_commit_of_that_repository(self):
        late = self.repo_with_commit("late", "2026-01-20T12:00:00")
        near = self.repo_with_commit("near", "2026-01-12T12:00:00")
        self.write(self.kb, "wiki/projects/late.md", "# late\n\n- 저장소: `%s`. 문서는 `docs/`\n" % late)
        self.write(self.kb, "wiki/projects/near.md", "# near\n\n- 위치: `%s`\n" % near)
        self.write(self.kb, "wiki/projects/gone.md", "# gone\n\n- 저장소: `%s`\n" % os.path.join(self.tmp, "없는-폴더"))
        self.write(self.kb, "wiki/projects/unknown.md", "# unknown\n\n- 저장소: 위치 미확인\n")
        for name in ("late", "near", "gone", "unknown", "no-card"):
            self.board(name, "2026-01-10")
        code, found = self.notices()
        self.assertEqual(code, 0)
        self.assertEqual(found, ["상황판 날짜: late 묶음 고친 날짜 2026-01-10, 저장소 최근 커밋 2026-01-20(10일 뒤)"])
        self.assertEqual(len(self.notices("--board-lag-days", "1")[1]), 2)

    def test_board_block_of_the_knowledge_base_itself_ignores_daily_record_commits(self):
        self.git(self.kb, "init", "-q")
        self.git(self.kb, "add", "INDEX.md" if os.path.exists(os.path.join(self.kb, "INDEX.md")) else "wiki")
        self.git(self.kb, "commit", "-q", "-m", "wiki", date="2026-01-20T12:00:00")
        self.write(self.kb, "wiki/projects/kb.md", "# kb\n\n- 저장소: `%s`\n" % self.kb)
        self.board("kb", "2026-01-10")
        self.assertEqual(self.notices(), (0, []))
        self.write(self.kb, "INDEX.md", "# 색인\n")
        self.git(self.kb, "add", "INDEX.md")
        self.git(self.kb, "commit", "-q", "-m", "index", date="2026-01-25T12:00:00")
        code, found = self.notices()
        self.assertEqual(found, ["상황판 날짜: kb 묶음 고친 날짜 2026-01-10, 저장소 최근 커밋 2026-01-25(15일 뒤)"])


class UsageTest(Base):

    def test_usage_errors(self):
        for args in ([], [self.kb, self.kb], [self.kb, "--nonsense"], [self.kb, "--today"], [self.kb, "--today", "어제"]):
            done = subprocess.run([sys.executable, SCRIPT] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(done.returncode, 1, args)
            self.assertIn("사용:", done.stderr.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
