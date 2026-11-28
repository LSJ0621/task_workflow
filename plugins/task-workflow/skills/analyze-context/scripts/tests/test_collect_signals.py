"""collect_signals.py 시험. 세션 기록과 지식 베이스는 전부 임시 폴더에 지어낸 것이다.
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
SCRIPT = os.path.join(os.path.dirname(HERE), "collect_signals.py")
DAY = "2026-01-06"
A = "aaaaaaaa-0000-4000-8000-000000000001"
B = "bbbbbbbb-0000-4000-8000-000000000002"
C = "cccccccc-0000-4000-8000-000000000003"


def uid(number):
    return "%08d-0000-4000-8000-000000000000" % number


def stamp(minute, day=DAY):
    # 03:00Z 는 서울에서 같은 날 12:00 이다. 시험은 TZ=Asia/Seoul 로 돌린다
    return "%sT03:%02d:00.000Z" % (day, minute)


def human(number, minute, text, day=DAY):
    return {"type": "user", "uuid": uid(number), "timestamp": stamp(minute, day), "isSidechain": False,
            "origin": {"kind": "human"}, "turnOrigin": "human", "message": {"role": "user", "content": text}}


def agent(number, minute, text, day=DAY):
    return {"type": "assistant", "uuid": uid(number), "timestamp": stamp(minute, day), "isSidechain": False,
            "message": {"role": "assistant", "model": "claude-fake-1", "content": [{"type": "text", "text": text}]}}


class CollectSignalsTest(unittest.TestCase):

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="collect-signals-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.kb = os.path.join(self.tmp, "kb")
        self.projects = os.path.join(self.tmp, "projects")
        self.out = os.path.join(self.tmp, "out")
        for folder in ("raw/journal", "raw/cases", "raw/decisions", "raw/context"):
            os.makedirs(os.path.join(self.kb, folder))
        os.makedirs(self.projects)

    def write(self, rel, text):
        path = os.path.join(self.kb, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def session(self, sid, rows, sub=None):
        target = os.path.join(self.projects, "-fake-app") if sub is None else os.path.join(self.projects, "-fake-app", sid, "subagents")
        os.makedirs(target, exist_ok=True)
        with open(os.path.join(target, (sub or sid) + ".jsonl"), "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def run_script(self, *args):
        env = dict(os.environ, TZ="Asia/Seoul")
        done = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, env=env)
        return done.returncode, done.stdout, done.stderr

    def candidates(self, *args):
        code, out, err = self.run_script("candidates", self.kb, "--projects-dir", self.projects, "--out", self.out, *args)
        self.assertEqual(code, 0, err)
        return out.strip().splitlines()

    def candidate_file(self, day=DAY):
        with open(os.path.join(self.out, day + ".candidates.md"), encoding="utf-8") as handle:
            return handle.read()

    def write_list(self, decisions, day=DAY):
        path = os.path.join(self.tmp, "decisions.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(decisions)
        return self.run_script("write", self.kb, "--projects-dir", self.projects, "--day", day, "--decisions", path)

    def read_list(self, day=DAY):
        with open(os.path.join(self.kb, "evolve", "signals", day + ".md"), encoding="utf-8") as handle:
            return handle.read()

    def build_day(self):
        self.session(A, [
            human(1, 0, "목록을 만들어 줘"), agent(2, 1, "지어낸 답의 머리. 확인할 것: 지어낸 줄"),
            human(3, 2, "<!-- reply 1 -->\n> 확인할 것: 지어낸 줄\n\n이건 무슨 뜻이야?"), agent(4, 3, "지어낸 풀이"),
            human(5, 4, "표는 빼라고 했잖아 | 다시 해"), agent(6, 5, "둘 중 무엇으로 할까요? 가 또는 나"),
            human(7, 6, "나로 해"), agent(8, 7, "지어낸 결과"),
            human(9, 8, "좋네 이대로 가자"),
            human(10, 0, "다음 날에 한 말", day="2026-01-07"),
        ])
        fake_key = "sk-" + "fake0" * 5   # 지어낸 값. 비밀값 모양만 흉내 낸다
        self.session(B, [
            human(21, 10, "서버 10.20.30.40 의 vpc-0123456789abcdef0 를 봐 줘"),
            human(22, 11, "키는 " + fake_key + " 야"),
            human(23, 12, "기록이 있는 지적"), agent(24, 13, "지어낸 답"), human(25, 14, "범위 밖의 말"),
        ])
        self.session(C, [   # 예약 작업 세션은 뺀다
            {"type": "user", "uuid": uid(31), "timestamp": stamp(0), "isSidechain": False, "promptSource": "sdk",
             "message": {"role": "user", "content": "<scheduled-task name=\"fake\">지어낸 지시</scheduled-task>"}},
            human(32, 1, "예약 작업 세션의 말"),
        ])
        self.session(A, [human(41, 0, "서브에이전트 기록의 말")], sub="agent-x")
        self.fake_key = fake_key
        self.write("raw/journal/%s.md" % DAY, "\n".join([
            "12:05 | feedback | 지어낸 작업 | 표를 넣었다. 사용자 말: \"표는 빼라고 했잖아\" 풀이: 표를 쓰지 않는다 | - | session:%s" % A,
            "12:30 | context | 지어낸 맥락 | 지어낸 사실. 사용자 말 없음 | - | session:%s" % A,
            "정리됨: 없음", ""]))
        self.write("raw/cases/C-20260106-01-fake.md",
                   "---\nid: C-20260106-01\ntype: case\ndate: %s\nstatus: active\nsession: %s\nrange: %s..%s\n---\n# 사례\n"
                   % (DAY, B, uid(23), uid(24)))

    # -- candidates -------------------------------------------------------

    def test_candidates_are_the_days_human_inputs(self):
        self.build_day()
        lines = self.candidates("--day", DAY)
        self.assertEqual(lines[0], "%s | 후보 9건 | %s" % (DAY, os.path.join(self.out, DAY + ".candidates.md")))
        self.assertEqual(lines[-1], "합계 1일")
        text = self.candidate_file()
        self.assertIn("그날 사람이 친 입력 9건이다.", text)
        self.assertNotIn("다음 날에 한 말", text)
        self.assertNotIn("예약 작업 세션의 말", text)
        self.assertNotIn("서브에이전트 기록의 말", text)
        block = text.split("## 00000003 | 12:02 | 세션 %s | 인용 답장\n" % A)[1].split("\n\n")[0]
        self.assertEqual(block.splitlines(), [
            "- 앞 답: 지어낸 답의 머리. 확인할 것: 지어낸 줄",
            "- 사용자: <!-- reply 1 --> > 확인할 것: 지어낸 줄 이건 무슨 뜻이야?",
            "- 같은 세션의 메모: 12:05 feedback 지어낸 작업; 12:30 context 지어낸 맥락",
            "- 이미 있는 메모·기록: 없음"])

    def test_candidates_show_what_already_has_memo_or_record(self):
        self.build_day()
        self.candidates("--day", DAY)
        text = self.candidate_file()

        def have(cid):
            return text.split("## %s | " % cid)[1].split("- 이미 있는 메모·기록: ")[1].splitlines()[0]
        self.assertEqual(have("00000005"), "메모 12:05")       # 메모가 그 말을 따옴표로 옮겼다
        self.assertEqual(have("00000007"), "없음")             # 같은 세션에 메모가 있어도 그 말을 옮기지 않았다
        self.assertEqual(have("00000023"), "C-20260106-01")    # 기록의 범위 안
        self.assertEqual(have("00000025"), "없음")             # 같은 세션이지만 범위 밖

    def test_candidates_hide_secrets_and_infra_identifiers(self):
        self.build_day()
        self.candidates("--day", DAY)
        text = self.candidate_file()
        self.assertIn("- 사용자: 서버 [가림] 의 [가림] 를 봐 줘", text)
        self.assertIn("- 사용자: [비밀값이 있어 가림]", text)
        self.assertNotIn(self.fake_key, text)
        self.assertNotIn("10.20.30.40", text)

    def test_copied_lines_in_continued_session_appear_once(self):
        first = [human(1, 0, "앞 세션에서 한 말"), agent(2, 1, "지어낸 답")]
        self.session(A, first + [human(3, 2, "앞 세션의 다음 말")])
        self.session(B, first + [human(4, 3, "이어 연 세션의 말")])
        self.assertEqual(self.candidates("--day", DAY)[0].split(" | ")[1], "후보 3건")
        self.assertEqual(self.candidate_file().count("앞 세션에서 한 말"), 1)

    def test_default_days_follow_the_newest_list(self):
        self.session(A, [human(1, 0, "지어낸 말")])
        days = lambda lines: [line.split(" | ")[0] for line in lines[:-1]]
        self.assertEqual(days(self.candidates("--today", "2026-01-10")), ["2026-01-09"])           # 목록이 없으면 어제
        self.write("evolve/signals/2026-01-06.md", "# 모은 말 2026-01-06\n")
        self.assertEqual(days(self.candidates("--today", "2026-01-10")), ["2026-01-07", "2026-01-08", "2026-01-09"])
        lines = self.candidates("--today", "2026-01-20")                                             # 많아도 7일
        self.assertEqual((days(lines)[0], days(lines)[-1], lines[-1]), ("2026-01-13", "2026-01-19", "합계 7일"))
        for day in range(13, 20):                                                                    # 7일 치 목록이 다 있으면 모을 날이 없다
            self.write("evolve/signals/2026-01-%d.md" % day, "# 모은 말 2026-01-%d\n" % day)
        self.assertEqual(self.candidates("--today", "2026-01-20"), ["합계 0일"])

    def test_days_without_a_list_are_collected_again(self):
        self.session(A, [human(1, 0, "지어낸 말")])
        days = lambda lines: [line.split(" | ")[0] for line in lines[:-1]]
        self.write("evolve/signals/2026-01-06.md", "# 모은 말 2026-01-06\n")
        self.write("evolve/signals/2026-01-08.md", "# 모은 말 2026-01-08\n")
        self.assertEqual(days(self.candidates("--today", "2026-01-09")), ["2026-01-07"])            # 목록 사이에 빠진 날
        self.assertEqual(days(self.candidates("--today", "2026-01-11")), ["2026-01-07", "2026-01-09", "2026-01-10"])
        self.assertEqual(days(self.candidates("--today", "2026-01-15")),                              # 7일 전보다 앞선 빈 날은 놓는다
                         ["2026-01-09", "2026-01-10", "2026-01-11", "2026-01-12", "2026-01-13", "2026-01-14"])
        self.write("evolve/signals/2026-01-19.md", "# 모은 말 2026-01-19\n")
        self.assertEqual(days(self.candidates("--today", "2026-01-20")),
                         ["2026-01-13", "2026-01-14", "2026-01-15", "2026-01-16", "2026-01-17", "2026-01-18"])
        self.assertEqual(days(self.candidates("--today", "2026-01-07")), [])                         # 가장 오래된 목록보다 앞선 날은 보지 않는다


    # -- write --------------------------------------------------------------

    def test_write_builds_the_days_list(self):
        self.build_day()
        code, out, err = self.write_list("\n".join([
            "# 가른 결과", "",
            "00000003 | 다시 물음",
            "00000005 | 지적",                       # 스크립트가 찾은 메모를 쓴다
            "00000007 | 선택 | -",
            "00000009 | 만족 | 메모 12:30",          # 가른 쪽이 메모를 정했다
            "00000021 | 지적 | 없음 | 가림",
            "00000022 | 지적",
            "00000023 | 지적",
        ]))
        self.assertEqual(code, 0, err)
        self.assertIn("사용자 입력 9건 가운데 7줄. 지적 4(메모·기록 없음 2), 다시 물음 1, 만족 1, 선택 1.", out)
        text = self.read_list()
        self.assertTrue(text.startswith("# 모은 말 %s\n" % DAY))
        self.assertIn("| 시각 | 세션 | 종류 | 사용자 말 | 메모·기록 |", text)
        rows = [line for line in text.splitlines() if line.startswith("| 12:")]
        self.assertEqual(rows, [
            "| 12:02 | %s | 다시 물음 | <!-- reply 1 --> > 확인할 것: 지어낸 줄 이건 무슨 뜻이야? | 없음 |" % A,
            "| 12:04 | %s | 지적 | 표는 빼라고 했잖아 / 다시 해 | 메모 12:05 |" % A,
            "| 12:06 | %s | 선택 | 나로 해 | 없음 |" % A,
            "| 12:08 | %s | 만족 | 좋네 이대로 가자 | 메모 12:30 |" % A,
            "| 12:10 | %s | 지적 | [가림] | 없음 |" % B,
            "| 12:11 | %s | 지적 | [비밀값이 있어 가림] | 없음 |" % B,
            "| 12:12 | %s | 지적 | 기록이 있는 지적 | C-20260106-01 |" % B,
        ])
        self.assertNotIn(self.fake_key, text)

    def test_write_cuts_words_to_80_chars_and_overwrites(self):
        self.session(A, [human(1, 0, "가" * 200)])
        self.assertEqual(self.write_list("00000001 | 지적\n")[0], 0)
        self.assertIn("| 지적 | %s | 없음 |" % ("가" * 80), self.read_list())
        self.assertEqual(self.write_list("")[0], 0)                       # 실을 것이 없는 날도 목록을 쓴다
        text = self.read_list()
        self.assertIn("사용자 입력 1건 가운데 0줄.", text)
        self.assertNotIn("가" * 80, text)

    def test_write_to_another_folder_leaves_knowledge_base_alone(self):
        self.session(A, [human(1, 0, "지어낸 말")])
        path = os.path.join(self.tmp, "decisions.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("00000001 | 만족\n")
        elsewhere = os.path.join(self.tmp, "elsewhere")
        code, out, err = self.run_script("write", self.kb, "--projects-dir", self.projects, "--day", DAY,
                                         "--decisions", path, "--list-dir", elsewhere)
        self.assertEqual(code, 0, err)
        self.assertTrue(os.path.isfile(os.path.join(elsewhere, DAY + ".md")))
        self.assertFalse(os.path.exists(os.path.join(self.kb, "evolve")))

    def test_write_rejects_unreadable_decisions(self):
        self.build_day()
        for bad in ("99999999 | 지적", "00000003 | 칭찬", "00000003 | 지적 | 어딘가", "00000003", "00000003 | 지적\n00000003 | 만족"):
            code, _, err = self.write_list(bad + "\n")
            self.assertEqual(code, 1, bad)
            self.assertTrue(err.strip())
        self.assertFalse(os.path.exists(os.path.join(self.kb, "evolve", "signals", DAY + ".md")))


if __name__ == "__main__":
    unittest.main()
