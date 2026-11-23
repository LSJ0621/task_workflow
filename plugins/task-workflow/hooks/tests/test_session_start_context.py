"""session_start_context.py 시험. 지식 베이스와 저장소 폴더는 임시 폴더에 지어낸 것이다.
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
HOOKS = os.path.dirname(HERE)
SCRIPT = os.path.join(HOOKS, "session_start_context.py")


class SessionStartContextTest(unittest.TestCase):

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="session-start-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.kb = os.path.join(self.tmp, "kb")
        self.app = os.path.join(self.tmp, "dev", "app")
        self.inner = os.path.join(self.app, "packages", "inner")
        self.other = os.path.join(self.tmp, "dev", "app-other")
        for folder in (os.path.join(self.kb, "wiki", "projects"), os.path.join(self.app, "src"), self.inner, self.other):
            os.makedirs(folder)
        self.write("wiki/projects/app.md", (
            "# app\n\n- 뭐 하는 프로젝트: 지어낸 앱\n- 저장소: `%s` (GitHub `fake/app`). 문서는 그 저장소의 `docs/`\n\n"
            "## 유효한 결정\n- 아래 탭으로 이동한다 (D-20260105-02)\n" % self.app))
        self.write("wiki/projects/inner.md", "# inner\n\n- 위치: `%s`\n\n## 유효한 결정\n- 없음\n" % self.inner)
        self.write("wiki/projects/nowhere.md", "# nowhere\n\n- 저장소: 위치 미확인. 루트에 `docker-compose.yml`\n")
        self.write("wiki/board.md", (
            "# 상황판\n\n설명 글.\n\n"
            "## other\n- 어디까지: 다른 프로젝트의 일\n- 고친 날짜: 2026-01-01\n\n"
            "## app\n- 어디까지: 로그인 화면까지\n- 다음 할 일: 결제 화면\n- 막힌 것: 없음\n- 고친 날짜: 2026-01-05\n\n"
            "## inner\n- 어디까지: 안쪽 꾸러미\n- 고친 날짜: 2026-01-06\n"))

    def write(self, rel, text):
        with open(os.path.join(self.kb, rel), "w", encoding="utf-8") as handle:
            handle.write(text)

    def hook(self, cwd, source="startup", kb="default", raw=None):
        env = dict(os.environ)
        env.pop("KNOWLEDGE_BASE_DIR", None)
        env.pop("CLAUDE_PROJECT_DIR", None)
        if kb is not None:
            env["KNOWLEDGE_BASE_DIR"] = self.kb if kb == "default" else kb
        payload = raw if raw is not None else json.dumps({
            "session_id": "abc123", "transcript_path": "/fake/transcript.jsonl", "cwd": cwd,
            "hook_event_name": "SessionStart", "source": source, "model": "claude-fake-1"})
        done = subprocess.run([sys.executable, SCRIPT], input=payload.encode("utf-8"),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")

    def test_prints_card_and_only_that_board_block(self):
        code, out, err = self.hook(self.app)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("프로젝트 `app`", out)
        self.assertIn("[프로젝트 카드: wiki/projects/app.md]\n# app\n", out)
        self.assertIn("- 아래 탭으로 이동한다 (D-20260105-02)", out)
        self.assertIn("[상황판: wiki/board.md 의 app 묶음]\n## app\n- 어디까지: 로그인 화면까지\n", out)
        self.assertTrue(out.rstrip().endswith("- 고친 날짜: 2026-01-05"))
        for word in ("다른 프로젝트의 일", "안쪽 꾸러미", "설명 글", "# inner", "# nowhere"):
            self.assertNotIn(word, out)
        self.assertFalse(out.lstrip().startswith("{"))   # 글자 출력으로 읽혀야 한다

    def test_folder_below_the_repository_matches(self):
        self.assertIn("프로젝트 `app`", self.hook(os.path.join(self.app, "src"))[1])

    def test_longest_matching_repository_wins(self):
        out = self.hook(self.inner)[1]
        self.assertIn("프로젝트 `inner`", out)
        self.assertIn("## inner\n- 어디까지: 안쪽 꾸러미", out)
        self.assertNotIn("로그인 화면까지", out)

    def test_nothing_when_no_project_matches(self):
        for folder in (self.other, self.tmp, os.path.dirname(self.app), "/"):
            self.assertEqual(self.hook(folder), (0, "", ""), folder)

    def test_nothing_on_resume_and_fork_but_printed_on_clear_and_compact(self):
        for source in ("resume", "fork"):
            self.assertEqual(self.hook(self.app, source), (0, "", ""))
        for source in ("startup", "clear", "compact"):
            self.assertIn("프로젝트 `app`", self.hook(self.app, source)[1])

    def test_nothing_without_knowledge_base(self):
        self.assertEqual(self.hook(self.app, kb=None), (0, "", ""))
        self.assertEqual(self.hook(self.app, kb=os.path.join(self.tmp, "없는-폴더")), (0, "", ""))
        self.assertEqual(self.hook(self.app, kb=self.app), (0, "", ""))

    def test_bad_input_is_silent(self):
        for raw in ("", "깨진 입력", "[]", '{"source": "startup"}', '{"cwd": 3}'):
            self.assertEqual(self.hook(self.app, raw=raw), (0, "", ""), raw)

    def test_card_without_board_block(self):
        self.write("wiki/board.md", "# 상황판\n\n## other\n- 어디까지: 다른 일\n")
        out = self.hook(self.app)[1]
        self.assertIn("[프로젝트 카드: wiki/projects/app.md]", out)
        self.assertNotIn("상황판:", out)
        self.assertNotIn("다른 일", out)

    def test_git_worktree_of_the_repository_matches(self):
        tree = os.path.join(self.tmp, "trees", "feature")
        os.makedirs(os.path.join(tree, "src"))
        with open(os.path.join(tree, ".git"), "w", encoding="utf-8") as handle:
            handle.write("gitdir: %s/.git/worktrees/feature\n" % self.app)
        self.assertIn("프로젝트 `app`", self.hook(os.path.join(tree, "src"))[1])

    def test_long_output_is_cut_below_the_hook_limit(self):
        self.write("wiki/board.md", "# 상황판\n\n## app\n- 어디까지: " + "가" * 20000 + "\n- 고친 날짜: 2026-01-05\n")
        self.write("wiki/projects/app.md", "# app\n\n- 저장소: `%s`\n\n## 유효한 결정\n" % self.app + "- 결정 줄\n" * 3000)
        out = self.hook(self.app)[1]
        self.assertLess(len(out), 10000)
        self.assertIn("이 줄의 뒤는 wiki/board.md 에서 읽는다", out)
        self.assertIn("- 고친 날짜: 2026-01-05", out)   # 긴 줄 뒤의 줄이 밀려나지 않는다
        self.assertIn("뒤는 wiki/projects/app.md 에서 읽는다", out)

    def test_hook_is_registered_for_session_start(self):
        with open(os.path.join(HOOKS, "hooks.json"), encoding="utf-8") as handle:
            config = json.load(handle)
        commands = [hook["command"] for group in config["hooks"]["SessionStart"] for hook in group["hooks"]
                    if hook["type"] == "command"]
        self.assertEqual(len(commands), 1)
        self.assertIn("session_start_context.py", commands[0])
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", commands[0])
        self.assertIn("UserPromptSubmit", config["hooks"])


if __name__ == "__main__":
    unittest.main()
