"""structure_history.py 시험. 지식 베이스와 저장소는 임시 폴더에 지어낸 것이다.
돌리기: python3 -m unittest discover -s <이 폴더>
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "structure_history.py")


class StructureHistoryTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="structure-history-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.kb = os.path.join(self.tmp, "kb")
        os.makedirs(os.path.join(self.kb, "raw", "decisions"))
        self.repo = os.path.join(self.tmp, "fake-plugin")
        os.makedirs(self.repo)
        self.git("init", "-q")
        self.commit("2026-01-03T10:00:00", "스킬 report-check를 더한다", {"skills/report-check/SKILL.md": "v1", "README.md": "v1"})
        self.commit("2026-01-03T15:00:00", "README를 고친다", {"README.md": "v2"})
        self.commit("2026-01-07T09:00:00", "보고서 확인 문장을 고친다", {"skills/report-check/SKILL.md": "v2",
                                                                     "skills/report-check/references/how.md": "v1"})
        self.commit("2026-01-09T09:00:00", "훅을 더한다\n\nreport-check가 놓치는 것을 훅이 잡는다", {"hooks/guard.py": "v1"})
        self.commit("2026-01-12T09:00:00", "아침 확인을 없앤다", {}, remove=["skills/report-check"])
        self.decision("D-20260102-01", "2026-01-02", "active", "[skills, structure]", "보고서를 다른 눈으로 확인하는 스킬을 더한다",
                      "## 요지\n스킬 `report-check`를 더했다.\n\n## 이유와 근거\n만든 쪽이 놓친다.\n\n## 바뀐 것\nskills/report-check\n")
        self.decision("D-20260112-01", "2026-01-12", "active", "[structure]", "아침 확인을 없앤다",
                      "## 요지\n### 결정\n\n`report-check` 스킬을 지웠다. 표 | 는 쓰지 않는다.\n\n### 이유\n매일 볼 필요가 없다.\n")
        self.decision("D-20260105-01", "2026-01-05", "superseded", "[report]", "보고는 두 줄로 한다",
                      "## 결정\nreport-check 가 두 줄만 본다.\n\n## 이유\n길면 안 읽는다.\n")
        self.decision("D-20260106-01", "2026-01-06", "active", "[other]", "대화에만 이름이 나오는 결정",
                      "## 있었던 일\n<!-- extract:start -->\n**사용자** (10:00)\n> report-check 얘기\n<!-- extract:end -->\n\n## 요지\n다른 일.\n")

    def git(self, *args, date="2026-01-01T00:00:00"):
        env = dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date, GIT_AUTHOR_NAME="t",
                   GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        subprocess.run(["git", "-C", self.repo] + list(args), check=True, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def commit(self, date, message, files, remove=()):
        for rel, text in files.items():
            path = os.path.join(self.repo, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        for rel in remove:
            self.git("rm", "-rq", rel)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message, date=date)

    def decision(self, rid, date, status, tags, title, body):
        with open(os.path.join(self.kb, "raw", "decisions", rid + "-fake.md"), "w", encoding="utf-8") as handle:
            handle.write("---\nid: %s\ntype: decision\ntitle: %s\ndate: %s\nscope: me\nstatus: %s\ntags: %s\n---\n\n# %s\n\n%s"
                         % (rid, title, date, status, tags, title, body))

    def run_script(self, *args, kb=True):
        env = dict(os.environ)
        env.pop("KNOWLEDGE_BASE_DIR", None)
        extra = ["--knowledge-base", self.kb] if kb else []
        done = subprocess.run([sys.executable, SCRIPT] + list(args) + extra + ["--repo", self.repo],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")

    def rows(self, out):
        return [line.split(" | ") for line in out.splitlines() if " | " in line]

    def test_decisions_and_commits_in_date_order(self):
        code, out, err = self.run_script("report-check")
        self.assertEqual(code, 0, err)
        lines = out.splitlines()
        self.assertEqual(lines[:2], ["이름: report-check", "지금 있는 경로(fake-plugin): 없음"])
        rows = self.rows(out)
        self.assertTrue(all(len(row) == 5 for row in rows))
        self.assertEqual([(row[0], row[1], row[3]) for row in rows], [
            ("2026-01-02", "구조 결정", "보고서를 다른 눈으로 확인하는 스킬을 더한다"),
            ("2026-01-03", "커밋", "스킬 report-check를 더한다"),
            ("2026-01-05", "결정", "보고는 두 줄로 한다"),
            ("2026-01-07", "커밋", "보고서 확인 문장을 고친다"),
            ("2026-01-09", "커밋", "훅을 더한다"),
            ("2026-01-12", "구조 결정", "아침 확인을 없앤다"),
            ("2026-01-12", "커밋", "아침 확인을 없앤다"),
        ])
        self.assertEqual(rows[0][2], "D-20260102-01 (active)")
        self.assertEqual(rows[0][4], "스킬 `report-check`를 더했다.")
        self.assertEqual(rows[2][2], "D-20260105-01 (superseded)")
        self.assertEqual(rows[5][4], "`report-check` 스킬을 지웠다. 표 / 는 쓰지 않는다.")
        self.assertTrue(rows[1][2].startswith("fake-plugin "))
        self.assertEqual(rows[1][4], "skills/report-check/SKILL.md (더함 1)")
        self.assertEqual(rows[3][4].split(" (")[1], "더함 1, 고침 1)")
        self.assertEqual(rows[4][4], "커밋 메시지에 이름이 나옴")
        self.assertIn("(지움 2)", rows[6][4])
        self.assertNotIn("README를 고친다", out)
        self.assertNotIn("대화에만 이름이 나오는 결정", out)

    def test_name_that_still_exists(self):
        out = self.run_script("guard")[1]
        self.assertIn("지금 있는 경로(fake-plugin): hooks/guard.py", out)
        self.assertEqual([row[3] for row in self.rows(out)], ["훅을 더한다"])

    def test_nothing_found(self):
        code, out, _ = self.run_script("no-such-thing")
        self.assertEqual(code, 0)
        self.assertIn("찾지 못했다", out)
        self.assertEqual(self.rows(out), [])

    def test_without_knowledge_base_only_commits(self):
        code, out, _ = self.run_script("report-check", kb=False)
        self.assertEqual(code, 0)
        self.assertIn("결정 기록은 찾지 않았다", out)
        self.assertEqual({row[1] for row in self.rows(out)}, {"커밋"})

    def test_limit_keeps_the_latest(self):
        out = self.run_script("report-check", "--limit", "2")[1]
        self.assertIn("오래된 5줄은 뺐다", out)
        self.assertEqual([row[0] for row in self.rows(out)], ["2026-01-12", "2026-01-12"])

    def test_errors(self):
        self.assertNotEqual(self.run_script()[0], 0)
        self.assertNotEqual(self.run_script("a*b")[0], 0)
        done = subprocess.run([sys.executable, SCRIPT, "x", "--repo", self.tmp], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(done.returncode, 0)
        done = subprocess.run([sys.executable, SCRIPT, "x", "--knowledge-base", self.repo, "--repo", self.repo],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(done.returncode, 0)


if __name__ == "__main__":
    unittest.main()
