"""list_active.py 시험. 지식 베이스는 임시 폴더에 지어낸 것이다.
돌리기: python3 -m unittest discover -s <이 폴더>
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "list_active.py")


class ListActiveTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="list-active-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.kb = os.path.join(self.tmp, "kb")
        for folder in ("cases", "decisions", "context"):
            os.makedirs(os.path.join(self.kb, "raw", folder))
        self.record("decisions", "D-20260105-01", "me", "active", "보고는 두 줄로 한다",
                    "## 있었던 일\n<!-- extract:start -->\n발췌: raw/sessions/x.md a..b\n<!-- extract:end -->\n\n"
                    "## 요지\n### 결정\n\n작업이 끝나면 두 줄로 보고한다. 표 | 는 쓰지 않는다.\n둘째 줄.\n\n### 이유\n길면 안 읽는다.\n")
        self.record("decisions", "D-20260105-02", "project:app", "active", "앱은 탭으로 이동한다",
                    "## 정해야 했던 것\n이동 방식.\n\n## 결정\n아래 탭으로 이동한다.\n\n## 이유\n익숙하다.\n")
        self.record("decisions", "D-20260105-03", "project:app", "superseded", "앱은 햄버거로 이동한다", "## 결정\n햄버거.\n")
        self.record("decisions", "D-20260105-04", "project:app", "archived", "시안 다섯 화면", "## 결정\n다섯 화면.\n")
        self.record("decisions", "D-20260105-05", "me", "draft", "아직 확인 전", "## 요지\n아직 없음\n")
        self.record("context", "X-20260105-01", "me", "active", "저녁에 개인 프로젝트를 한다",
                    "## 사실\n주중 저녁에 개인 프로젝트를 한다.\n\n## 유효 기간\n변할 수 있음.\n")
        self.record("context", "X-20260105-02", "project:app", "active", "오늘 서버가 켜져 있다", "## 사실\n켜짐.\n", "snapshot: true\n")
        self.record("context", "X-20260105-03", "project:other", "active", "본문이 없는 기록", "")
        self.record("cases", "C-20260105-01", "me", "active", "사례는 찍지 않는다", "## 요지\n사례.\n", kind="case")

    def record(self, folder, rid, scope, status, title, body, extra="", kind=None):
        kind = kind or {"decisions": "decision", "context": "context"}[folder]
        with open(os.path.join(self.kb, "raw", folder, rid + "-fake.md"), "w", encoding="utf-8") as handle:
            handle.write("---\nid: %s\ntype: %s\ntitle: %s\ndate: 2026-01-05\nscope: %s\nstatus: %s   # 설명\n%s---\n\n# %s\n\n%s"
                         % (rid, kind, title, scope, status, extra, title, body))

    def run_script(self, *args, env=None):
        base = dict(os.environ)
        base.pop("KNOWLEDGE_BASE_DIR", None)
        base.update(env or {})
        done = subprocess.run([sys.executable, SCRIPT] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=base)
        return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")

    def test_lists_only_active_decisions_and_contexts(self):
        code, out, err = self.run_script(self.kb)
        self.assertEqual(code, 0, err)
        self.assertEqual(out, (
            "D-20260105-01 | 보고는 두 줄로 한다 | 작업이 끝나면 두 줄로 보고한다. 표 / 는 쓰지 않는다.\n"
            "D-20260105-02 | 앱은 탭으로 이동한다 | 아래 탭으로 이동한다.\n"
            "X-20260105-01 | 저녁에 개인 프로젝트를 한다 | 주중 저녁에 개인 프로젝트를 한다.\n"
            "X-20260105-03 | 본문이 없는 기록 | -\n"
        ))

    def test_scope_filter(self):
        self.assertEqual([line.split(" | ")[0] for line in self.run_script(self.kb, "--scope", "me")[1].splitlines()],
                         ["D-20260105-01", "X-20260105-01"])
        self.assertEqual([line.split(" | ")[0] for line in self.run_script(self.kb, "--scope", "project:app")[1].splitlines()],
                         ["D-20260105-02"])
        both = self.run_script(self.kb, "--scope", "me", "project:other")[1].splitlines()
        self.assertEqual(len(both), 3)
        self.assertEqual(self.run_script(self.kb, "--scope", "me", "--scope", "project:other")[1].splitlines(), both)
        self.assertEqual(self.run_script(self.kb, "--scope", "project:none"), (0, "", ""))

    def test_knowledge_base_path_after_scope_is_not_read_as_a_scope(self):
        want = self.run_script(self.kb, "--scope", "project:app")
        self.assertEqual(want[0], 0)
        self.assertEqual(self.run_script("--scope", "project:app", self.kb), want)
        self.assertEqual(self.run_script("--scope", "me", "project:other", self.kb),
                         self.run_script(self.kb, "--scope", "me", "project:other"))
        self.assertEqual(self.run_script("--type", "context", "--scope", "me", self.kb)[1].splitlines()[0][:13], "X-20260105-01")
        # 경로를 따로 줬으면 범위 자리의 다른 값은 그대로 틀린 범위다
        code, out, err = self.run_script(self.kb, "--scope", "me", self.kb)
        self.assertNotEqual(code, 0)
        self.assertIn("--scope 값이", err)
        code, out, err = self.run_script("--scope", "me", "everyone")
        self.assertNotEqual(code, 0)
        self.assertIn("--scope 값이", err)

    def test_type_filter(self):
        out = self.run_script(self.kb, "--type", "context")[1]
        self.assertEqual([line[:13] for line in out.splitlines()], ["X-20260105-01", "X-20260105-03"])

    def test_every_row_has_three_cells(self):
        for line in self.run_script(self.kb)[1].splitlines():
            self.assertEqual(len(line.split(" | ")), 3, line)

    def test_knowledge_base_from_environment(self):
        code, out, _ = self.run_script("--scope", "me", env={"KNOWLEDGE_BASE_DIR": self.kb})
        self.assertEqual((code, len(out.splitlines())), (0, 2))

    def test_errors(self):
        self.assertNotEqual(self.run_script()[0], 0)
        self.assertNotEqual(self.run_script(self.tmp)[0], 0)
        self.assertNotEqual(self.run_script(self.kb, "--scope", "everyone")[0], 0)


if __name__ == "__main__":
    unittest.main()
