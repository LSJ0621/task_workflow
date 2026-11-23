"""check_rule_change.py 시험. 규칙 저장소, 지식 베이스, 한도 파일은 전부 임시 폴더에 지어낸 것이다.
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
SCRIPT = os.path.join(os.path.dirname(HERE), "check_rule_change.py")
EVOLVE = "누가 정했는지: 자가 발전"
USER = "누가 정했는지: 사용자"

GUIDE = (
    "# 전역 지침\n\n"
    "## 원칙\n- 정확성이 먼저다.\n- 묻는 건 두 경우뿐이다(예: 삭제, 배포).\n\n"
    "## 보고\n- 두 줄로 보고한다.\n- 부작용을 적는다(예: 권한 규칙이 안 읽힌다).\n"
)
STYLE = "# 응답 양식\n\n## 설명 순서\n- 결론부터 쓴다.\n\n## 단어 고르기\n- 쉬운 말로 쓴다.\n"


class Base(unittest.TestCase):

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="rule-change-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = os.path.join(self.tmp, "rules")
        self.kb = os.path.join(self.tmp, "kb")
        self.limits = os.path.join(self.tmp, "evolve", "limits.json")
        os.makedirs(os.path.join(self.kb, "raw", "decisions"))
        with open(os.path.join(self.kb, "raw", "decisions", "D-20260105-01-add-hook.md"), "w", encoding="utf-8") as handle:
            handle.write("---\nid: D-20260105-01\ntype: decision\nstatus: active\ntags: [structure]\n---\n# 훅을 더한다\n")
        os.makedirs(self.repo)
        self.git("init", "-q")
        self.write("CLAUDE.md", GUIDE)
        self.write("output-styles/style.md", STYLE)
        self.write("skills/helper/SKILL.md", "# 도우미\n\n## 순서\n- 하나씩 한다.\n")
        self.write("evolve/state.md", "# 상태\n")
        self.commit("처음", date="2026-01-01T09:00:00")
        code, out, err = self.script("init-limits", "--repo", self.repo, "--limits", self.limits)
        self.assertEqual(code, 0, err)

    def env(self, extra=None):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        for name in ("KNOWLEDGE_BASE_DIR", "RULE_CHANGE_WHO", "RULE_CHANGE_DECISION", "RULE_CHANGE_LIMITS",
                     "CLAUDE_CONFIG_DIR", "GIT_DIR", "GIT_INDEX_FILE"):
            env.pop(name, None)
        env.update(extra or {})
        return env

    def git(self, *args, date=None, extra=None, check=True):
        env = self.env(extra)
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        done = subprocess.run(["git", "-C", self.repo] + list(args), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check and done.returncode != 0:
            raise AssertionError(done.stderr.decode("utf-8"))
        return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")

    def write(self, rel, text, stage=True):
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        if stage:
            self.git("add", rel)

    def commit(self, message, date="2026-01-02T09:00:00"):
        self.git("commit", "-q", "-m", message, date=date)

    def script(self, *args, extra=None):
        done = subprocess.run([sys.executable, SCRIPT] + list(args), env=self.env(extra),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")

    def check(self, *args, extra=None, today="2026-01-10"):
        # 시험 커밋의 날짜가 2026년 1월 초라 검사하는 날도 그 무렵으로 준다(3번 검사의 창이 오늘에서 거꾸로 세기 때문이다)
        code, out, err = self.script("--repo", self.repo, "--limits", self.limits, "--knowledge-base", self.kb,
                                     "--today", today, *args, extra=extra)
        blocks = [line.strip()[len("[막음] "):] for line in out.splitlines() if line.strip().startswith("[막음]")]
        notices = [line.strip()[len("[알림] "):] for line in out.splitlines() if line.strip().startswith("[알림]")]
        return code, blocks, notices, out + err


class LimitsFileTest(Base):

    def test_first_values_are_the_sizes_at_that_time(self):
        with open(self.limits, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["chars"], {"CLAUDE.md": len(GUIDE), "output-styles/style.md": len(STYLE)})
        self.assertEqual(data["root"], self.repo)
        self.assertEqual((data["examples_per_section"], data["edits_per_section"], data["edits_window_days"]), (1, 2, 30))

    def test_existing_limits_file_is_kept_unless_forced(self):
        with open(self.limits, encoding="utf-8") as handle:
            before = handle.read()
        code, out, err = self.script("init-limits", "--repo", self.repo, "--limits", self.limits, "--examples", "9")
        self.assertEqual(code, 2)
        with open(self.limits, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), before)
        code, out, err = self.script("init-limits", "--repo", self.repo, "--limits", self.limits, "--force",
                                     "--files", "CLAUDE.md", "--examples", "4", "--edits", "3", "--window-days", "14")
        self.assertEqual(code, 0, err)
        with open(self.limits, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual((list(data["chars"]), data["examples_per_section"], data["edits_per_section"], data["edits_window_days"]),
                         (["CLAUDE.md"], 4, 3, 14))
        self.assertEqual(self.script("init-limits", "--repo", self.repo, "--limits", self.limits, "--force",
                                     "--window-days", "0")[0], 2)

    def test_missing_file_is_an_error(self):
        self.assertEqual(self.script("init-limits", "--repo", self.repo, "--limits", self.limits + "2", "--files", "없는.md")[0], 2)


class CharsTest(Base):

    def test_nothing_staged_passes(self):
        code, blocks, notices, out = self.check()
        self.assertEqual((code, blocks, notices), (0, [], []))
        self.assertIn("통과", out)

    def test_growing_past_the_limit_is_blocked(self):
        self.write("CLAUDE.md", GUIDE + "- 한 줄 더.\n")
        code, blocks, notices, out = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(len(blocks), 1)
        self.assertIn("글자 수: CLAUDE.md %d자, 한도 %d자" % (len(GUIDE) + 9, len(GUIDE)), blocks[0])
        self.assertIn("막음 1건", out)

    def test_same_size_or_smaller_passes(self):
        self.write("CLAUDE.md", GUIDE.replace("정확성이 먼저다", "정확성이 우선이다"[:8]))
        self.assertEqual(self.check()[0], 0)
        self.write("output-styles/style.md", STYLE.replace("- 쉬운 말로 쓴다.\n", ""))
        self.assertEqual(self.check()[:2], (0, []))

    def test_user_decided_change_is_only_a_notice(self):
        self.write("CLAUDE.md", GUIDE + "- 한 줄 더.\n")
        code, blocks, notices, _ = self.check("--who", "user")
        self.assertEqual((code, blocks), (0, []))
        self.assertTrue(any(line.startswith("글자 수: CLAUDE.md") for line in notices))
        self.assertEqual(self.check(extra={"RULE_CHANGE_WHO": "user"})[0], 0)
        self.assertEqual(self.check(extra={"RULE_CHANGE_WHO": "evolve"})[0], 1)

    def test_file_already_over_limit_may_shrink_but_not_grow(self):
        self.write("CLAUDE.md", GUIDE + "- 사용자가 더한 긴 줄 하나.\n- 또 한 줄.\n")
        self.commit("전역 지침에 두 줄\n\n" + USER)
        self.write("CLAUDE.md", GUIDE + "- 사용자가 더한 긴 줄 하나.\n")
        code, blocks, notices, _ = self.check()
        self.assertEqual((code, blocks), (0, []))
        self.assertTrue(any("늘지 않았다" in line for line in notices))
        self.write("CLAUDE.md", GUIDE + "- 사용자가 더한 긴 줄 하나.\n- 또 한 줄.\n- 셋째 줄.\n")
        self.assertEqual(self.check()[0], 1)

    def test_limits_apply_only_to_the_repository_they_were_made_for(self):
        other = os.path.join(self.tmp, "other")
        shutil.copytree(self.repo, other)
        with open(os.path.join(other, "CLAUDE.md"), "a", encoding="utf-8") as handle:
            handle.write("- 긴 줄.\n" * 50)
        subprocess.run(["git", "-C", other, "add", "CLAUDE.md"], check=True, env=self.env())
        code, out, err = self.script("--repo", other, "--limits", self.limits)
        self.assertEqual(code, 0, out + err)

    def test_without_limits_file_chars_are_skipped_with_a_notice(self):
        self.write("CLAUDE.md", GUIDE + "- 한 줄 더.\n")
        code, out, err = self.script("--repo", self.repo, "--limits", os.path.join(self.tmp, "없음.json"))
        self.assertEqual(code, 0, out + err)
        self.assertIn("한도 파일이 없어", out)


class ExamplesTest(Base):

    def test_more_examples_than_the_limit_in_one_section_is_blocked(self):
        self.write("skills/helper/SKILL.md", "# 도우미\n\n## 순서\n- 하나씩 한다(예: 가). 예: 나.\n")
        code, blocks, _, _ = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(blocks, ['"예:" 개수: skills/helper/SKILL.md "순서" 절 2개, 한도 1개(커밋 전 0개)'])
        self.assertEqual(self.check("--who", "user")[:2], (0, []))

    def test_examples_spread_over_sections_pass(self):
        self.write("skills/helper/SKILL.md", "# 도우미\n\n## 순서\n- 하나씩 한다(예: 가).\n\n## 보고\n- 짧게(예: 나).\n")
        self.assertEqual(self.check()[:2], (0, []))

    def test_section_already_over_the_limit_is_blocked_only_when_it_grows(self):
        self.write("skills/helper/SKILL.md", "# 도우미\n\n## 순서\n- 예: 가. 예: 나. 예: 다.\n")
        self.commit("예를 셋 넣음\n\n" + USER)
        self.write("skills/helper/SKILL.md", "# 도우미\n\n## 순서\n- 예: 가. 예: 나. 예: 다.\n- 예가 아닌 줄.\n")
        self.assertEqual(self.check()[:2], (0, []))
        self.write("skills/helper/SKILL.md", "# 도우미\n\n## 순서\n- 예: 가. 예: 나. 예: 다. 예: 라.\n")
        self.assertEqual(self.check()[0], 1)

    def test_files_that_are_not_rule_documents_are_not_counted(self):
        self.write("evolve/state.md", "# 상태\n\n## 보류\n- 예: 가. 예: 나. 예: 다. 예: 라.\n")
        self.write("skills/helper/assets/template.md", "## 틀\n- 예: 가. 예: 나. 예: 다.\n")
        self.assertEqual(self.check()[:2], (0, []))


class RepeatTest(Base):

    def edit(self, text, message, date):
        self.write("output-styles/style.md", text)
        self.commit(message, date=date)

    def twice(self):
        self.edit(STYLE.replace("결론부터 쓴다.", "결론부터 쓴다. 왜를 붙인다."), "설명 순서 1\n\n" + EVOLVE, "2026-01-03T09:00:00")
        self.edit(STYLE.replace("결론부터 쓴다.", "결론을 먼저 쓴다."), "설명 순서 2\n\n누가 정했나: 자가 발전", "2026-01-04T09:00:00")

    def repeated(self, *args, **kwargs):
        """(종료 코드, 되풀이 알림이 났는지). 되풀이는 막지 않고 알림만 낸다."""
        code, blocks, notices, _ = self.check(*args, **kwargs)
        self.assertFalse(any(line.startswith("같은 절 되풀이") for line in blocks))
        return code, any(line.startswith("같은 절 되풀이") for line in notices)

    def test_third_sentence_edit_of_a_section_by_self_evolve_is_only_a_notice(self):
        # 다른 방식으로 고쳐 쓰거나 틀린 문장을 빼는 것까지 막지 않으려고 알림만 낸다
        self.twice()
        self.write("output-styles/style.md", STYLE.replace("결론부터 쓴다.", "답부터 쓴다."))
        code, blocks, notices, _ = self.check()
        self.assertEqual((code, blocks), (0, []))
        hit = [line for line in notices if line.startswith("같은 절 되풀이")]
        self.assertEqual(len(hit), 1)
        self.assertIn('같은 절 되풀이: output-styles/style.md "설명 순서" 절을 자가 발전이 2025-12-11부터 이미 2번 고쳤다', hit[0])
        self.assertIn("막지 않는다", hit[0])

    def test_second_edit_and_other_sections_pass(self):
        self.edit(STYLE.replace("결론부터 쓴다.", "결론을 먼저 쓴다."), "설명 순서 1\n\n" + EVOLVE, "2026-01-03T09:00:00")
        self.write("output-styles/style.md", STYLE.replace("결론부터 쓴다.", "답부터 쓴다."))
        self.assertEqual(self.check()[:2], (0, []))
        self.commit("설명 순서 2\n\n" + EVOLVE, date="2026-01-04T09:00:00")
        self.write("output-styles/style.md", STYLE.replace("결론부터 쓴다.", "답부터 쓴다.").replace("쉬운 말로", "아는 말로"))
        self.assertEqual(self.check()[:2], (0, []))

    def test_only_removing_lines_is_not_blocked(self):
        self.twice()
        self.write("output-styles/style.md", STYLE.replace("- 결론부터 쓴다.\n", ""))
        self.assertEqual(self.check()[:2], (0, []))

    def test_edits_decided_by_user_are_not_counted(self):
        self.edit(STYLE.replace("결론부터 쓴다.", "결론을 먼저 쓴다."), "설명 순서 1\n\n" + EVOLVE, "2026-01-03T09:00:00")
        self.edit(STYLE.replace("결론부터 쓴다.", "결론만 쓴다."), "설명 순서 2\n\n누가 정했나: 사용자가 정함", "2026-01-04T09:00:00")
        self.edit(STYLE.replace("결론부터 쓴다.", "결론을 쓴다."), "설명 순서 3 (표시 없음)", "2026-01-05T09:00:00")
        self.write("output-styles/style.md", STYLE.replace("결론부터 쓴다.", "답부터 쓴다."))
        self.assertEqual(self.check()[:2], (0, []))

    def test_user_decided_third_edit_is_only_a_notice(self):
        self.twice()
        self.write("output-styles/style.md", STYLE.replace("결론부터 쓴다.", "답부터 쓴다."))
        code, blocks, notices, _ = self.check("--who", "user")
        self.assertEqual((code, blocks), (0, []))
        self.assertTrue(any(line.startswith("같은 절 되풀이") for line in notices))

    def set_limit(self, **values):
        with open(self.limits, encoding="utf-8") as handle:
            data = json.load(handle)
        data.update(values)
        with open(self.limits, "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    def test_only_edits_inside_the_window_are_counted(self):
        self.twice()   # 자가 발전이 2026-01-03과 2026-01-04에 고쳤다
        self.write("output-styles/style.md", STYLE.replace("결론부터 쓴다.", "답부터 쓴다."))
        self.assertEqual(self.repeated(today="2026-02-02"), (0, True))    # 30일 전은 01-03. 두 번 다 창 안이다
        self.assertEqual(self.repeated(today="2026-02-03"), (0, False))   # 30일 전은 01-04. 한 번만 창 안이다
        self.assertEqual(self.repeated(today="2026-06-01"), (0, False))   # 오래 지나면 알림도 없다

    def test_window_length_comes_from_the_limits_file(self):
        self.twice()
        self.write("output-styles/style.md", STYLE.replace("결론부터 쓴다.", "답부터 쓴다."))
        self.assertEqual(self.repeated(today="2026-02-20"), (0, False))
        self.set_limit(edits_window_days=60)
        code, _, notices, _ = self.check(today="2026-02-20")
        self.assertEqual(code, 0)
        self.assertTrue(any("2025-12-22부터 이미 2번" in line for line in notices))
        self.set_limit(edits_window_days=0)
        self.assertEqual(self.check()[0], 2)

    def test_edits_since_is_used_when_it_is_later_than_the_window_start(self):
        self.twice()
        self.write("output-styles/style.md", STYLE.replace("결론부터 쓴다.", "답부터 쓴다."))
        self.set_limit(edits_since="2026-01-04")            # 창의 시작(2025-12-11)보다 늦다. 01-04의 한 번만 센다
        self.assertEqual(self.repeated(), (0, False))
        self.set_limit(edits_since="2026-01-03")
        self.assertEqual(self.repeated(), (0, True))
        self.set_limit(edits_since="2025-01-01")            # 창의 시작보다 이르면 창의 시작부터 센다
        self.assertEqual(self.repeated(today="2026-02-03"), (0, False))
        self.assertEqual(self.repeated(today="2026-02-02"), (0, True))
        self.set_limit(edits_since="작년")
        self.assertEqual(self.check()[0], 2)


class StructureTest(Base):

    def test_structure_file_needs_a_decision_record(self):
        self.write("hooks/guard.py", "print('x')\n")
        code, blocks, _, _ = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(blocks, ['구조 결정 기록: 구조를 바꿨는데(hooks/guard.py) 결정 기록 id가 없다. '
                                  '형식은 사서 스킬 기록 규칙의 "구조 결정 기록" 절'])
        code, blocks, _, _ = self.check("--decision", "D-20260105-09")
        self.assertEqual(code, 1)
        self.assertIn("D-20260105-09이 지식 베이스 raw/decisions/ 에 없다", blocks[0])
        self.assertIn('형식은 사서 스킬 기록 규칙의 "구조 결정 기록" 절', blocks[0])
        self.assertEqual(self.check("--decision", "D-20260105-01")[:2], (0, []))
        self.assertEqual(self.check(extra={"RULE_CHANGE_DECISION": "D-20260105-01"})[:2], (0, []))

    def test_user_decided_structure_change_still_needs_a_record(self):
        self.write("hooks/guard.py", "print('x')\n")
        self.assertEqual(self.check("--who", "user")[0], 1)
        self.assertEqual(self.check("--who", "user", "--decision", "D-20260105-01")[0], 0)

    def test_without_knowledge_base_a_record_cannot_be_confirmed(self):
        self.write("hooks/guard.py", "print('x')\n")
        code, out, err = self.script("--repo", self.repo, "--limits", self.limits, "--decision", "D-20260105-01")
        self.assertEqual(code, 1, out + err)
        self.assertIn("지식 베이스를 몰라", out)
        code, out, err = self.script("--repo", self.repo, "--limits", self.limits, "--decision", "D-20260105-01",
                                     extra={"KNOWLEDGE_BASE_DIR": self.kb})
        self.assertEqual(code, 0, out + err)

    def test_what_counts_as_structure(self):
        for rel in ("skills/helper/scripts/run.py", "bin/tool", "scheduled-tasks/daily/SKILL.md",
                    "skills/new-one/SKILL.md", "agents/checker.md", "plugins/p/hooks/hooks.json"):
            self.write(rel, "x\n")
            self.assertEqual(self.check()[0], 1, rel)
            self.git("reset", "-q", "--", rel)
        self.git("rm", "-q", "--cached", "skills/helper/SKILL.md")
        self.assertEqual(self.check()[0], 1)
        self.git("reset", "-q", "--", "skills/helper/SKILL.md")
        # 있는 스킬 문서의 문장을 고치는 것, 상태 파일, 그 밖의 파일은 구조가 아니다
        self.write("skills/helper/SKILL.md", "# 도우미\n\n## 순서\n- 둘씩 한다.\n")
        self.write("evolve/state.md", "# 상태\n- 고침\n")
        self.write("settings.json", "{}\n")
        self.write("skills/helper/references/more.md", "## 더\n- 글.\n")
        self.assertEqual(self.check()[:2], (0, []))


class StructureScopeTest(Base):
    """4번 검사는 구조를 더하거나 지우거나 옮긴 것만 막는다. 있는 스크립트를 고치는 것은 알림만 낸다."""

    def setUp(self):
        Base.setUp(self)
        for rel in ("hooks/guard.py", "hooks/hooks.json", "bin/tool", "skills/helper/scripts/run.py",
                    "skills/daily-upkeep/SKILL.md", "scheduled-tasks/daily/SKILL.md", "agents/checker.md",
                    "plugins/p/skills/daily-upkeep/SKILL.md", "plugins/p/skills/s/scripts/run.py", "plugins/p/hooks/hooks.json",
                    "mods/monitor/hooks/register.py"):
            self.write(rel, "# 처음\n\n## 절\n- 처음 글.\n")
        self.commit("구조 파일들\n\n" + USER)

    def change(self, rel):
        self.write(rel, "# 처음\n\n## 절\n- 고친 글.\n")

    def test_editing_an_existing_script_or_hook_is_only_a_notice(self):
        for rel in ("hooks/guard.py", "bin/tool", "skills/helper/scripts/run.py", "plugins/p/skills/s/scripts/run.py"):
            self.change(rel)
            code, blocks, notices, _ = self.check()
            self.assertEqual((code, blocks), (0, []), rel)
            self.assertEqual(notices, ["구조 파일 수정: 있는 구조 파일을 고치기만 했다(%s). 결정 기록 없이 통과시킨다" % rel])
            # 결정 기록을 주면 알림도 없다
            self.assertEqual(self.check("--decision", "D-20260105-01")[:3], (0, [], []))
            self.git("reset", "-q", "--hard")

    def test_editing_flow_files_needs_a_decision_record(self):
        for rel in ("skills/daily-upkeep/SKILL.md", "plugins/p/skills/daily-upkeep/SKILL.md", "scheduled-tasks/daily/SKILL.md",
                    "hooks/hooks.json", "plugins/p/hooks/hooks.json"):
            self.change(rel)
            code, blocks, _, _ = self.check()
            self.assertEqual(code, 1, rel)
            self.assertIn("구조 결정 기록", blocks[-1])
            self.assertEqual(self.check("--decision", "D-20260105-01")[0], 0, rel)
            self.git("reset", "-q", "--hard")

    def test_editing_skill_and_agent_documents_is_a_rule_change_not_a_structure_change(self):
        self.change("skills/helper/SKILL.md")
        self.change("agents/checker.md")
        self.assertEqual(self.check()[:3], (0, [], []))

    def test_adding_removing_or_moving_in_structure_folders_is_blocked(self):
        self.git("rm", "-q", "hooks/guard.py")
        self.assertEqual(self.check()[0], 1)
        self.git("reset", "-q", "--hard")
        self.git("mv", "skills/helper/scripts/run.py", "skills/helper/scripts/go.py")
        self.assertEqual(self.check()[0], 1)
        self.git("reset", "-q", "--hard")
        self.git("mv", "agents/checker.md", "agents/verifier.md")
        self.assertEqual(self.check()[0], 1)

    def test_tests_and_hooks_folders_elsewhere_are_not_structure(self):
        for rel in ("skills/helper/scripts/tests/test_run.py", "hooks/tests/test_guard.py", "plugins/p/hooks/tests/test_x.py",
                    "mods/monitor/hooks/new.py", "mods/monitor/bin/tool", "plugins/p/bin/tool", "docs/scripts/x.py",
                    "skills/helper/references/scripts/x.py"):
            self.write(rel, "x\n")
        self.change("mods/monitor/hooks/register.py")
        self.assertEqual(self.check()[:3], (0, [], []))

    def test_audit_uses_the_same_scope(self):
        self.git("tag", "review-1")
        self.change("skills/helper/scripts/run.py")
        self.commit("스크립트 버그를 고친다\n\n" + EVOLVE, date="2026-01-03T09:00:00")
        self.change("mods/monitor/hooks/register.py")
        self.commit("모니터를 고친다", date="2026-01-04T09:00:00")
        self.change("hooks/hooks.json")
        self.commit("훅 등록을 고친다\n\n" + EVOLVE, date="2026-01-05T09:00:00")
        self.write("skills/helper/scripts/new.py", "x\n")
        self.commit("스크립트를 더한다 D-20260105-01\n\n" + EVOLVE, date="2026-01-06T09:00:00")
        code, out, err = self.script("--audit", "--since", "review-1", "--repo", self.repo, "--limits", self.limits,
                                     "--knowledge-base", self.kb)
        self.assertEqual(code, 1, err)
        heads = [row.split(" | ")[1] for row in out.splitlines() if " | " in row]
        self.assertEqual(heads, ["스크립트 버그를 고친다", "훅 등록을 고친다"])
        self.assertEqual(len([row for row in out.splitlines() if "[알림] 구조 파일 수정" in row]), 1)
        self.assertEqual(len([row for row in out.splitlines() if "[어김] 구조 결정 기록" in row]), 1)
        self.assertEqual(out.splitlines()[-1],
                         "요약: 규칙 문서나 구조 파일을 건드린 커밋 3개, 어긴 커밋 1개(어김 1건), 알림 1건, 누가 정했는지 없는 커밋 0개")


class WhoDecidedTest(Base):
    """누가 정했는지는 그 말로 시작하는 줄만 본다. 설명 문장 가운데에 나온 말은 보지 않는다."""

    def edit(self, text, message, date):
        self.write("output-styles/style.md", text)
        self.commit(message, date=date)

    def test_phrase_inside_a_sentence_does_not_make_a_self_evolve_commit(self):
        told = '검사 스크립트: 자가 발전의 커밋인지는 메시지의 "누가 정했는지: 자가 발전"으로 안다.\n\n  ' + USER
        self.edit(STYLE.replace("결론부터 쓴다.", "결론을 먼저 쓴다."), "설명 순서 1\n\n" + told, "2026-01-03T09:00:00")
        self.edit(STYLE.replace("결론부터 쓴다.", "결론만 쓴다."), "설명 순서 2\n\n" + told, "2026-01-04T09:00:00")
        self.write("output-styles/style.md", STYLE.replace("결론부터 쓴다.", "답부터 쓴다."))
        self.assertEqual(self.check()[:2], (0, []))

    def test_line_with_leading_spaces_and_old_wording_still_counts(self):
        self.edit(STYLE.replace("결론부터 쓴다.", "결론을 먼저 쓴다."), "설명 순서 1\n\n   " + EVOLVE + ".", "2026-01-03T09:00:00")
        self.edit(STYLE.replace("결론부터 쓴다.", "결론만 쓴다."), "설명 순서 2\n\n근거: 없음\n누가 정했나: 자가 발전", "2026-01-04T09:00:00")
        self.write("output-styles/style.md", STYLE.replace("결론부터 쓴다.", "답부터 쓴다."))
        code, blocks, notices, _ = self.check()
        self.assertEqual((code, blocks), (0, []))
        self.assertTrue(any(line.startswith("같은 절 되풀이") for line in notices))   # 두 커밋 다 자가 발전으로 셌다

    def test_audit_reads_who_from_the_line_not_the_sentence(self):
        self.git("tag", "review-1")
        self.write("CLAUDE.md", GUIDE + "- 사용자가 더한 줄.\n")
        self.commit('전역 지침: 줄을 더한다\n\n설명에 "누가 정했는지: 자가 발전"이라는 말이 나온다.\n' + USER, date="2026-01-03T09:00:00")
        code, out, err = self.script("--audit", "--since", "review-1", "--repo", self.repo, "--limits", self.limits)
        self.assertEqual(code, 0, out + err)
        self.assertIn("2026-01-03 사용자 | 전역 지침: 줄을 더한다", out)
        self.assertIn("[알림] 글자 수", out)


class HookTest(Base):

    def install(self, *extra):
        return self.script("install-hook", "--repo", self.repo, "--limits", self.limits, "--knowledge-base", self.kb, *extra)

    def test_installed_hook_blocks_and_passes_real_commits(self):
        code, out, err = self.install()
        self.assertEqual(code, 0, err)
        hook = os.path.join(self.repo, ".git", "hooks", "pre-commit")
        self.assertTrue(os.access(hook, os.X_OK))
        self.write("CLAUDE.md", GUIDE + "- 한 줄 더.\n")
        code, out, err = self.git("commit", "-q", "-m", "늘림", check=False)
        self.assertNotEqual(code, 0)
        self.assertIn("[막음] 글자 수: CLAUDE.md", out + err)
        self.assertEqual(self.git("log", "--format=%s", "-1")[1].strip(), "처음")
        code, out, err = self.git("commit", "-q", "-m", "늘림\n\n" + USER, check=False, extra={"RULE_CHANGE_WHO": "user"})
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.git("log", "--format=%s", "-1")[1].strip(), "늘림")

    def test_hook_checks_only_what_this_commit_takes(self):
        self.install()
        self.write("CLAUDE.md", GUIDE + "- 다른 작업자가 스테이징해 둔 줄.\n")
        self.write("notes.txt", "메모\n")
        code, out, err = self.git("commit", "-q", "-m", "메모만", "--", "notes.txt", check=False)
        self.assertEqual(code, 0, out + err)
        self.assertNotEqual(self.git("commit", "-q", "-m", "전역 지침", "--", "CLAUDE.md", check=False)[0], 0)

    def test_hook_needs_decision_for_structure_change(self):
        self.install()
        self.write("hooks/guard.py", "print('x')\n")
        self.assertNotEqual(self.git("commit", "-q", "-m", "훅", check=False)[0], 0)
        code, out, err = self.git("commit", "-q", "-m", "훅 D-20260105-01", check=False,
                                  extra={"RULE_CHANGE_DECISION": "D-20260105-01"})
        self.assertEqual(code, 0, out + err)

    def test_other_hook_is_not_overwritten_unless_forced(self):
        hook = os.path.join(self.repo, ".git", "hooks", "pre-commit")
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        with open(hook, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\nexit 0\n")
        self.assertEqual(self.install()[0], 2)
        with open(hook, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "#!/bin/sh\nexit 0\n")
        self.assertEqual(self.install("--force")[0], 0)
        self.assertTrue(os.path.isfile(hook + ".before-rule-check"))
        self.assertEqual(self.install()[0], 0)   # 자기가 건 훅은 다시 걸 수 있다

    def test_hook_lets_commits_through_when_script_is_gone(self):
        copy = os.path.join(self.tmp, "copy.py")
        shutil.copy(SCRIPT, copy)
        self.assertEqual(self.install("--script", copy)[0], 0)
        os.remove(copy)
        self.write("CLAUDE.md", GUIDE + "- 한 줄 더.\n")
        code, out, err = self.git("commit", "-q", "-m", "늘림", check=False)
        self.assertEqual(code, 0)
        self.assertIn("검사하지 못했다", err)


class AuditTest(Base):

    def test_audit_reports_commits_that_should_have_been_blocked(self):
        self.git("tag", "review-1")
        self.write("CLAUDE.md", GUIDE + "- 자가 발전이 더한 줄.\n")
        self.commit("전역 지침 보고: 줄을 더한다\n\n" + EVOLVE, date="2026-01-03T09:00:00")
        self.write("CLAUDE.md", GUIDE + "- 자가 발전이 더한 줄.\n- 사용자가 더한 줄.\n")
        self.commit("전역 지침 보고: 사용자가 줄을 더한다\n\n" + USER, date="2026-01-04T09:00:00")
        self.write("hooks/guard.py", "print('x')\n")
        self.commit("훅을 더한다\n\n근거: D-20260105-01\n" + EVOLVE, date="2026-01-05T09:00:00")
        self.write("hooks/other.py", "print('y')\n")
        self.commit("훅을 하나 더 더한다", date="2026-01-06T09:00:00")
        self.write("evolve/state.md", "# 상태\n- 고침\n")
        self.commit("자가 발전 상태", date="2026-01-07T09:00:00")
        code, out, err = self.script("--audit", "--since", "review-1", "--repo", self.repo, "--limits", self.limits,
                                     "--knowledge-base", self.kb)
        self.assertEqual(code, 1, err)
        lines = out.splitlines()
        self.assertIn("review-1..HEAD 커밋 5개", lines[0])
        heads = [line for line in lines if " | " in line]
        self.assertEqual([line.split(" | ")[1] for line in heads],
                         ["전역 지침 보고: 줄을 더한다", "전역 지침 보고: 사용자가 줄을 더한다", "훅을 하나 더 더한다"])
        self.assertIn("2026-01-03 자가 발전", heads[0])
        self.assertIn("2026-01-04 사용자", heads[1])
        self.assertIn("표시 없음", heads[2])
        self.assertEqual(len([line for line in lines if "[어김] 글자 수" in line]), 1)
        self.assertEqual(len([line for line in lines if "[알림] 글자 수" in line]), 1)
        self.assertEqual(len([line for line in lines if "[어김] 구조 결정 기록" in line]), 1)
        self.assertNotIn("자가 발전 상태", out)
        self.assertEqual(lines[-1], "요약: 규칙 문서나 구조 파일을 건드린 커밋 4개, 어긴 커밋 2개(어김 2건), 알림 2건, 누가 정했는지 없는 커밋 1개")

    def audit(self, *extra):
        return self.script("--audit", "--since", "review-1", "--repo", self.repo, "--limits", self.limits, *extra)

    def test_audit_counts_repeats_in_the_window_before_each_commit(self):
        self.git("tag", "review-1")
        line = "결론부터 쓴다."
        for number, day in enumerate(("2026-01-03", "2026-01-04", "2026-03-01", "2026-03-05", "2026-03-06"), 1):
            self.write("output-styles/style.md", STYLE.replace(line, "%d번 고친 줄." % number))   # 글자 수는 그대로다
            self.commit("설명 순서 %d\n\n%s" % (number, EVOLVE), date=day + "T09:00:00")
        code, out, err = self.audit("--knowledge-base", self.kb)
        self.assertEqual(code, 0, err)   # 되풀이는 어김이 아니라 알림이다
        # 3번째(03-01)는 앞의 두 번이 30일 창 밖이라 알림이 없다. 5번째(03-06)는 창 안에 3·4번째가 있다
        hits = [row for row in out.splitlines() if "같은 절 되풀이" in row]
        self.assertEqual(len(hits), 1)
        self.assertIn("[알림]", hits[0])
        self.assertIn("2026-02-04부터 이미 2번", hits[0])
        self.assertIn("설명 순서 5", out)

    def merged_branch(self, message):
        """main 에 직접 한 구조 커밋 하나와, 구조 커밋 둘이 든 브랜치를 머지 커밋으로 합친 이력을 만든다."""
        self.git("tag", "review-1")
        self.git("checkout", "-q", "-b", "feat")
        self.write("hooks/a.py", "print('a')\n")
        self.commit("브랜치: 훅을 더한다\n\n" + USER, date="2026-01-03T09:00:00")
        self.write("skills/helper/scripts/run.py", "print('b')\n")
        self.write("CLAUDE.md", GUIDE + "- 브랜치에서 자가 발전이 더한 줄.\n")
        self.commit("브랜치: 스크립트를 더하고 전역 지침을 늘린다\n\n" + EVOLVE, date="2026-01-04T09:00:00")
        self.git("checkout", "-q", "-")
        self.write("hooks/direct.py", "print('c')\n")
        self.commit("바로 한 훅 커밋\n\n" + USER, date="2026-01-05T09:00:00")
        self.git("merge", "-q", "--no-ff", "-m", message, "feat", date="2026-01-06T09:00:00")

    def flagged(self, out):
        return [(row.split(" | ")[1], [line.strip() for line in out.splitlines()
                                       if line.strip().startswith("[어김]")]) for row in out.splitlines() if " | " in row]

    def test_decision_id_on_a_merge_commit_covers_the_commits_it_brought_in(self):
        self.merged_branch("Merge pull request #1 from fake/feat\n\n구조 개편 (D-20260105-01)")
        code, out, err = self.audit("--knowledge-base", self.kb)
        self.assertEqual(code, 1, err)
        lines = out.splitlines()
        self.assertIn("review-1..HEAD 커밋 3개", lines[0])
        self.assertTrue(lines[1].startswith("머지 "))
        self.assertIn("결정 기록 D-20260105-01을 그 머지로 들어온 커밋 2개의 결정 기록으로 쳤다", lines[1])
        kinds = [line for line in lines if "[어김]" in line]
        # 머지로 들어온 커밋의 구조 결정 기록은 어김이 아니다. 글자 수 같은 다른 검사는 그대로 본다
        self.assertEqual(len([line for line in kinds if "구조 결정 기록" in line]), 1)
        self.assertEqual(len([line for line in kinds if "글자 수" in line]), 1)
        heads = [row.split(" | ")[1] for row in lines if " | " in row]
        self.assertEqual(heads, ["브랜치: 스크립트를 더하고 전역 지침을 늘린다", "바로 한 훅 커밋"])
        self.assertIn("어긴 커밋 2개(어김 2건)", lines[-1])

    def test_merge_commit_id_is_not_used_when_that_record_does_not_exist(self):
        self.merged_branch("Merge pull request #1 from fake/feat\n\n구조 개편 (D-20260105-09)")
        code, out, err = self.audit("--knowledge-base", self.kb)
        self.assertEqual(code, 1, err)
        self.assertNotIn("머지 ", out)
        self.assertEqual(len([line for line in out.splitlines() if "[어김] 구조 결정 기록" in line]), 3)

    def test_merge_commit_without_id_or_without_knowledge_base_covers_nothing(self):
        self.merged_branch("Merge branch 'feat'")
        out = self.audit("--knowledge-base", self.kb)[1]
        self.assertEqual(len([line for line in out.splitlines() if "[어김] 구조 결정 기록" in line]), 3)

    def test_merge_commit_id_needs_the_knowledge_base_to_be_confirmed(self):
        self.merged_branch("Merge pull request #1 from fake/feat\n\n구조 개편 (D-20260105-01)")
        code, out, err = self.audit()
        self.assertEqual(code, 1, err)
        self.assertNotIn("머지 ", out)
        self.assertEqual(len([line for line in out.splitlines() if "[어김] 구조 결정 기록" in line]), 3)

    def test_audit_with_nothing_wrong(self):
        self.git("tag", "review-1")
        self.write("output-styles/style.md", STYLE.replace("- 쉬운 말로 쓴다.\n", ""))
        self.commit("응답 양식: 줄을 뺀다\n\n" + EVOLVE)
        code, out, err = self.script("--audit", "--since", "review-1", "--repo", self.repo, "--limits", self.limits)
        self.assertEqual(code, 0, out + err)
        self.assertIn("어긴 커밋 0개", out)

    def test_audit_usage(self):
        self.assertEqual(self.script("--audit", "--repo", self.repo)[0], 2)
        self.assertEqual(self.script("--audit", "--since", "없는-태그", "--repo", self.repo)[0], 2)
        self.assertEqual(self.script("--repo", self.tmp)[0], 2)
        self.assertEqual(self.script("--repo", self.repo, "--who", "someone")[0], 2)


if __name__ == "__main__":
    unittest.main()
