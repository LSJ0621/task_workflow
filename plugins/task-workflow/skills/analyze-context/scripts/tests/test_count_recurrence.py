"""count_recurrence.py 시험. 세션 기록과 추정 기록은 전부 임시 폴더에 지어낸 것이다.
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
SCRIPT = os.path.join(os.path.dirname(HERE), "count_recurrence.py")
DAY = "2026-01-06"
A = "aaaaaaaa-0000-4000-8000-000000000001"
B = "bbbbbbbb-0000-4000-8000-000000000002"
C = "cccccccc-0000-4000-8000-000000000003"
QUOTE = "<!-- reply 1 -->\n> 지어낸 앞 답의 한 줄\n\n"


def uid(number):
    return "00000000-0000-4000-8000-%012d" % number


def stamp(minute, day=DAY):
    # 03:00Z 는 서울에서 같은 날 12:00 이다. 시험은 TZ=Asia/Seoul 로 돌린다
    return "%sT03:%02d:00.000Z" % (day, minute)


def human(number, minute, text, day=DAY, **more):
    row = {"type": "user", "uuid": uid(number), "timestamp": stamp(minute, day), "isSidechain": False,
           "origin": {"kind": "human"}, "turnOrigin": "human", "message": {"role": "user", "content": text}}
    row.update(more)
    return row


def agent(number, minute, text=None, skill=None, day=DAY):
    blocks = [{"type": "text", "text": text}] if text else []
    if skill:
        blocks.append({"type": "tool_use", "id": "t%d" % number, "name": "Skill", "input": {"skill": skill}})
    return {"type": "assistant", "uuid": uid(number), "timestamp": stamp(minute, day), "isSidechain": False,
            "message": {"role": "assistant", "model": "claude-fake-1", "content": blocks}}


def hook(number, minute, text, event="UserPromptSubmit", day=DAY):
    return {"type": "attachment", "uuid": uid(number), "timestamp": stamp(minute, day), "isSidechain": False,
            "attachment": {"type": "hook_success", "hookEvent": event, "hookName": event, "content": text, "stdout": text + "\n"}}


class CountRecurrenceTest(unittest.TestCase):

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="count-recurrence-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.projects = os.path.join(self.tmp, "projects")
        self.kb = os.path.join(self.tmp, "kb")
        os.makedirs(self.projects)

    def session(self, sid, rows, folder="-fake-app", sub=None):
        target = os.path.join(self.projects, folder) if sub is None else os.path.join(self.projects, folder, sid, "subagents")
        os.makedirs(target, exist_ok=True)
        with open(os.path.join(target, (sub or sid) + ".jsonl"), "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def run_script(self, *args):
        env = dict(os.environ, TZ="Asia/Seoul")
        done = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, env=env)
        return done.returncode, done.stdout, done.stderr

    def count(self, *args):
        code, out, err = self.run_script("count", "--projects-dir", self.projects, "--since", "2026-01-01", *args)
        self.assertEqual(code, 0, err)
        return out

    def last(self, *args):
        return self.count(*args).strip().splitlines()[-1]

    # -- 같은 턴에서 보는 조건 -------------------------------------------------

    def test_mark_on_input_and_hook_note_in_same_turn(self):
        self.session(A, [
            human(1, 0, QUOTE + "이건 무슨 뜻이야?"), hook(2, 0, "인용해 되묻는 입력이다"), agent(3, 1, "지어낸 답"),
            human(4, 2, QUOTE + "이 줄은?"), agent(5, 3, "지어낸 답"),                       # 훅 알림이 안 붙은 입력
            human(6, 4, "표시 없는 말"), hook(7, 4, "인용해 되묻는 입력이다"), agent(8, 5, "지어낸 답"),
            human(9, 6, QUOTE + "다른 훅"), hook(10, 6, "인용해 되묻는 입력이다", event="PostToolUse"),
        ])
        out = self.count("--same", "user:<!-- reply", "--recur", "hook:인용해 되묻는")
        self.assertEqual(out.strip().splitlines()[-1], "같은 상황 3번 중 재발 1번")
        self.assertIn("[같은 상황] %s 2026-01-06 12:00:00 user | <!-- reply 1 --> > 지어낸 앞 답의 한 줄 이건 무슨 뜻이야?" % A, out)
        self.assertIn("  [재발] %s 2026-01-06 12:00:00 hook | 인용해 되묻는 입력이다" % A, out)
        self.assertEqual(self.last("--same", "user:<!-- reply", "--recur", "!hook:인용해 되묻는"), "같은 상황 3번 중 재발 2번")
        self.assertEqual(self.last("--same", "user:<!-- reply", "--same", "user:무슨 뜻"), "같은 상황 1번")

    # -- 뒤 몇 턴 안에서 보는 조건 ----------------------------------------------

    def test_user_words_within_turns_after_agent_words(self):
        self.session(A, [
            human(1, 0, "목록 줘. 이건 뭐야"),                # --within 1 이상이면 같은 턴의 사용자 글은 재발로 보지 않는다
            agent(2, 1, "확인할 것: 지어낸 줄"),
            human(3, 2, "알겠어"), agent(4, 3, "지어낸 답"),
            human(5, 4, "아까 그 줄은 뭐야?"), agent(6, 5, "지어낸 답"),
            human(7, 6, "다음"), agent(8, 7, "확인할 것: 또 지어낸 줄"),
            human(9, 8, "이건 뭐야?"), agent(10, 9, "지어낸 답"),
        ])
        same, recur = ("--same", "agent:확인할 것"), ("--recur", "user:뭐야")
        self.assertEqual(self.last(*same, *recur), "같은 상황 2번 중 재발 1번")                  # 같은 턴만 본다(첫 턴의 사용자 글)
        self.assertEqual(self.last(*same, *recur, "--within", "1"), "같은 상황 2번 중 재발 1번")
        self.assertEqual(self.last(*same, *recur, "--within", "2"), "같은 상황 2번 중 재발 2번")

    def test_window_stops_at_next_same_situation(self):
        self.session(A, [
            human(1, 0, "첫째"), agent(2, 1, "확인할 것: 하나"),
            human(3, 2, "둘째"), agent(4, 3, "확인할 것: 둘"),
            human(5, 4, "이건 뭐야?"),
        ])
        out = self.count("--same", "agent:확인할 것", "--recur", "user:뭐야", "--within", "5")
        self.assertEqual(out.strip().splitlines()[-1], "같은 상황 2번 중 재발 1번")   # 재발 하나를 앞의 같은 상황에도 치지 않는다
        self.assertEqual(out.count("[재발]"), 1)

    # -- 스킬과 세션 단위 --------------------------------------------------------

    def test_skill_by_tool_and_by_slash_command_per_session(self):
        self.session(A, [
            human(1, 0, "나눠서 맡겨"), agent(2, 1, "지어낸 답", skill="fake-plugin:split-work"),
            human(3, 2, "계속"), agent(4, 3, skill="fake-plugin:split-work"),
            human(5, 4, "왜 이렇게 오래 걸려"),
        ])
        self.session(B, [human(11, 0, "/fake-plugin:split-work 지어낸 인자"), agent(12, 1, "지어낸 답"), human(13, 2, "좋아")])
        self.session(C, [human(21, 0, "/tmp/fake/path 를 봐"), agent(22, 1, "지어낸 답", skill="fake-plugin:other")])
        same, recur = ("--same", "skill:split-work"), ("--recur", "user:오래 걸")
        self.assertEqual(self.last(*same, *recur, "--within", "3"), "같은 상황 3번 중 재발 1번")
        out = self.count(*same, *recur, "--within", "3", "--per", "session")
        self.assertEqual(out.strip().splitlines()[-1], "같은 상황 2번 중 재발 1번")
        self.assertIn("단위: 세션", out)
        self.assertIn("skill | fake-plugin:split-work", out)
        self.assertEqual(self.last(*same, "--session", "bbbbbbbb"), "같은 상황 1번")

    # -- 빼는 것 -----------------------------------------------------------------

    def test_scheduled_subagent_and_sidechain_are_left_out(self):
        self.session(A, [human(1, 0, "세는 말"), agent(2, 1, "지어낸 답")])
        self.session(B, [
            {"type": "user", "uuid": uid(11), "timestamp": stamp(0), "isSidechain": False, "promptSource": "sdk",
             "message": {"role": "user", "content": "<scheduled-task name=\"fake\">세는 말</scheduled-task>"}},
            human(12, 1, "세는 말"),
        ])
        self.session(A, [human(21, 0, "세는 말")], sub="agent-x")              # 서브에이전트 기록 파일
        self.session(C, [human(31, 0, "세는 말", isSidechain=True),            # 서브에이전트 안쪽 대화
                         {"type": "mystery-kind", "uuid": uid(32), "timestamp": stamp(1)},   # 모르는 줄은 넘어간다
                         human(33, 2, "다른 말")])
        out = self.count("--same", "user:세는 말")
        self.assertEqual(out.strip().splitlines()[-1], "같은 상황 1번")
        self.assertIn("읽은 세션 2개, 뺀 예약 작업 세션 1개", out)

    def test_copied_lines_in_continued_session_count_once(self):
        first = [human(1, 0, "목록 줘"), agent(2, 1, "확인할 것: 하나")]
        self.session(A, first + [human(3, 2, "알겠어")])
        self.session(B, first + [human(4, 3, "이건 뭐야?")])                   # 이어 연 세션. 앞 두 줄은 같은 uuid로 복사돼 있다
        out = self.count("--same", "agent:확인할 것", "--recur", "user:뭐야", "--within", "1")
        self.assertEqual(out.strip().splitlines()[-1], "같은 상황 1번 중 재발 1번")
        self.assertIn("[같은 상황] %s" % A, out)
        self.assertIn("[재발] %s" % B, out)
        self.assertEqual(self.last("--same", "user:목록 줘"), "같은 상황 1번")

    # -- 기간, 찍는 글 -----------------------------------------------------------

    def test_period_is_local_time_and_until_date_is_inclusive(self):
        self.session(A, [human(1, 0, "세는 말", day="2026-01-05"), human(2, 0, "세는 말"), human(3, 30, "세는 말"),
                         human(4, 0, "세는 말", day="2026-01-08")])
        self.assertEqual(self.last("--same", "user:세는 말"), "같은 상황 4번")
        code, out, err = self.run_script("count", "--projects-dir", self.projects, "--since", "2026-01-06",
                                         "--until", "2026-01-06", "--same", "user:세는 말")
        self.assertEqual((code, out.strip().splitlines()[-1]), (0, "같은 상황 2번"), err)
        code, out, err = self.run_script("count", "--projects-dir", self.projects, "--since", "2026-01-06T12:10",
                                         "--until", "2026-01-08T11:00", "--same", "user:세는 말")
        self.assertEqual((code, out.strip().splitlines()[-1]), (0, "같은 상황 1번"), err)

    def test_shows_first_80_chars_match_place_and_hides_secret(self):
        long_text = "가" * 100 + " 여기 걸리는 낱말 " + "나" * 50
        fake_key = "sk-" + "fake0" * 5   # 지어낸 값. 비밀값 모양만 흉내 낸다
        self.session(A, [human(1, 0, "시작"), agent(2, 1, long_text), human(3, 2, "걸리는 낱말 " + fake_key)])
        out = self.count("--same", "agent:걸리는 낱말")
        self.assertIn("agent | " + "가" * 80 + " … 걸린 곳: ", out)
        self.assertIn("여기 걸리는 낱말", out)
        out = self.count("--same", "user:걸리는 낱말")
        self.assertIn("user | [비밀값이 있어 가림]", out)
        self.assertNotIn(fake_key, out)

    def test_json_output(self):
        self.session(A, [human(1, 0, QUOTE + "뭐야"), hook(2, 0, "인용해 되묻는 입력이다")])
        data = json.loads(self.count("--same", "user:<!-- reply", "--recur", "hook:인용해", "--json"))
        self.assertEqual((data["same"], data["recur"], data["unit"]), (1, 1, "턴"))
        self.assertEqual(data["hits"][0]["recur"][0]["where"], "hook")

    def test_bad_condition_is_an_error(self):
        for spec in ("user", "nowhere:말", "user:("):
            code, _, err = self.run_script("count", "--projects-dir", self.projects, "--since", "2026-01-01", "--same", spec)
            self.assertEqual(code, 1, spec)
            self.assertTrue(err.strip())

    # -- due ----------------------------------------------------------------------

    def test_due_lists_watching_trials_whose_day_has_come(self):
        os.makedirs(os.path.join(self.kb, "evolve"))
        with open(os.path.join(self.kb, "evolve", "hypotheses.md"), "w", encoding="utf-8") as handle:
            handle.write("\n".join([
                "# 추정 기록", "",
                "```markdown", "### 2025-01-08 본보기 안의 시도", "- 상태: 지켜보는 중", "- 볼 날짜: 2025-01-15", "```", "",
                "## 전역 지침 CLAUDE.md — 지어낸 절", "",
                "### 2026-01-01 볼 날짜가 지난 시도", "- 상태: 지켜보는 중", "- 종류: 시도", "- 볼 날짜: 2026-01-08",
                "- 셀 것: 같은 상황 = 지어낸 상황 / 재발 = 지어낸 재발", "- 결과: 2026-01-08 같은 상황 1번 중 재발 0번. 지어낸 위치", "",
                "### 2026-01-09 볼 날짜가 오늘인 시도", "- 상태: 지켜보는 중", "- 종류: 확인된 원인", "- 볼 날짜: 2026-01-16", "",
                "### 2026-01-12 아직 볼 날짜가 안 된 시도", "- 상태: 지켜보는 중", "- 볼 날짜: 2026-01-19", "",
                "## 플러그인 fake/SKILL.md — 지어낸 절", "",
                "### H-20260102-01 볼 날짜 줄이 없는 예전 시도", "- 상태: 지켜보는 중", "- 틀렸다고 볼 신호: 지어낸 신호", "",
                "### 2026-01-03 끝난 시도", "- 상태: 틀림 (2026-01-10)", "- 볼 날짜: 2026-01-10", "",
            ]))
        code, out, err = self.run_script("due", self.kb, "--today", "2026-01-16")
        self.assertEqual(code, 0, err)
        lines = out.strip().splitlines()
        self.assertEqual(lines[-1], "합계 3")
        self.assertEqual(lines[0], "전역 지침 CLAUDE.md — 지어낸 절 | 2026-01-01 볼 날짜가 지난 시도 | 볼 날짜: 2026-01-08 | 종류: 시도 | "
                                   "셀 것: 같은 상황 = 지어낸 상황 / 재발 = 지어낸 재발 | 결과 줄 1개")
        self.assertIn("2026-01-09 볼 날짜가 오늘인 시도 | 볼 날짜: 2026-01-16 | 종류: 확인된 원인 | 셀 것: 없음 | 결과 줄 0개", lines[1])
        self.assertIn("H-20260102-01 볼 날짜 줄이 없는 예전 시도 | 볼 날짜: 없음 | 종류: 없음", lines[2])

    def test_due_without_file_is_zero(self):
        os.makedirs(self.kb)
        code, out, _ = self.run_script("due", self.kb, "--today", "2026-01-16")
        self.assertEqual((code, out.strip()), (0, "합계 0"))


if __name__ == "__main__":
    unittest.main()
