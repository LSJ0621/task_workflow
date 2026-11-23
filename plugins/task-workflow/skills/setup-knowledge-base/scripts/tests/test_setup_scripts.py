"""bootstrap.py와 check_contract.py 시험. 대상 폴더는 임시 폴더다.
돌리기: python3 -m unittest discover -s <이 폴더>
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
NEW_FOLDERS = ("evolve", os.path.join("raw", "sessions"))


def run(script, *args):
    done = subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")


class Base(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="setup-kb-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.kb = os.path.join(self.tmp, "kb")

    def write(self, rel, text=""):
        path = os.path.join(self.kb, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)


class BootstrapTest(Base):

    def test_new_knowledge_base_has_the_folders_scripts_write_to(self):
        code, out, err = run("bootstrap.py", self.kb, "--name", "fake-wiki", "--owner", "아무개")
        self.assertEqual(code, 0, err)
        for folder in NEW_FOLDERS + (os.path.join("raw", "journal"), os.path.join("raw", "cases"),
                                     os.path.join("raw", "decisions"), os.path.join("raw", "context")):
            self.assertTrue(os.path.isdir(os.path.join(self.kb, folder)), folder)
        self.assertTrue(os.path.isfile(os.path.join(self.kb, "INDEX.md")))
        # 만든 초안은 계약 점검을 통과한다
        self.assertEqual(run("check_contract.py", self.kb)[0], 0)

    def test_existing_files_and_folders_are_left_alone(self):
        self.write("INDEX.md", "내 색인\n")
        self.write("evolve/metrics.md", "내 측정값\n")
        code, out, err = run("bootstrap.py", self.kb, "--name", "fake-wiki", "--owner", "아무개")
        self.assertEqual(code, 0, err)
        with open(os.path.join(self.kb, "INDEX.md"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "내 색인\n")
        with open(os.path.join(self.kb, "evolve", "metrics.md"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "내 측정값\n")
        self.assertIn("건너뜀: INDEX.md", out)
        again = run("bootstrap.py", self.kb, "--name", "fake-wiki", "--owner", "아무개")[1]
        self.assertIn("만든 파일 0개", again)
        self.assertNotIn("만든 빈 폴더", again)


class ContractTest(Base):

    def lines(self):
        code, out, _ = run("check_contract.py", self.kb)
        return code, [line.strip() for line in out.split("\n")[1:] if line.strip()]

    def test_required_items(self):
        os.makedirs(self.kb)
        self.assertEqual(self.lines()[0], 1)
        self.write("INDEX.md", "# 색인\n")
        self.assertEqual(self.lines()[0], 1)
        os.makedirs(os.path.join(self.kb, "raw", "journal"))
        self.assertEqual(self.lines()[0], 0)

    def test_new_folders_are_recommended_not_required(self):
        self.write("INDEX.md", "# 색인\n")
        os.makedirs(os.path.join(self.kb, "raw", "journal"))
        code, found = self.lines()
        self.assertEqual(code, 0)
        self.assertIn("[없음] 권장 · 자가 발전 폴더 (evolve/)", found)
        self.assertIn("[없음] 권장 · 규칙별 사례표 (evolve/rule-cases.md)", found)
        self.assertIn("[없음] 권장 · 세션 발췌 폴더 (raw/sessions/)", found)
        os.makedirs(os.path.join(self.kb, "raw", "sessions"))
        self.write("evolve/rule-cases.md", "| 사례 | 한 줄 요약 | 관련 규칙 | 규칙과 관계 |\n")
        code, found = self.lines()
        self.assertIn("[있음] 권장 · 자가 발전 폴더 (evolve/)", found)
        self.assertIn("[있음] 권장 · 규칙별 사례표 (evolve/rule-cases.md)", found)
        self.assertIn("[있음] 권장 · 세션 발췌 폴더 (raw/sessions/)", found)
        self.assertFalse([line for line in found if line.startswith("[경고]")])

    def test_old_locations_and_old_table_head_are_warned(self):
        self.write("INDEX.md", "# 색인\n")
        os.makedirs(os.path.join(self.kb, "raw", "journal"))
        self.write("wiki/rule-cases.md", "| 사례 | 한 줄 요약 | 관련 규칙 | 규칙과 관계 |\n")
        self.write("wiki/hypotheses.md", "# 추정 기록\n")
        self.write("evolve/rule-cases.md", "| 사례 | 요약 |\n")
        code, found = self.lines()
        self.assertEqual(code, 0)
        warned = [line for line in found if line.startswith("[경고]")]
        self.assertEqual(len(warned), 3)
        self.assertTrue(any("wiki/rule-cases.md" in line and "evolve/rule-cases.md" in line for line in warned))
        self.assertTrue(any("wiki/hypotheses.md" in line and "evolve/hypotheses.md" in line for line in warned))
        self.assertTrue(any("표 머리" in line for line in warned))


if __name__ == "__main__":
    unittest.main()
