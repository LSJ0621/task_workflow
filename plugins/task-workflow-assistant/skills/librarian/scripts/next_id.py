#!/usr/bin/env python3
"""다음 식별자를 계산한다. 사용: next_id.py <지식 베이스> <종류 접두: C|D|X|R|B> [YYYYMMDD]
같은 날 같은 종류의 기존 파일을 세어 NN을 하나 올린다. 손으로 세면 겹치기 쉬워서 스크립트로 둔다."""
import datetime, pathlib, re, sys

FOLDER = {"C": "raw/cases", "D": "raw/decisions", "X": "raw/context", "R": "raw/reviews", "B": "raw/reports"}

def main():
    if len(sys.argv) < 3 or sys.argv[2] not in FOLDER:
        sys.exit("사용: next_id.py <지식 베이스> <C|D|X|R|B> [YYYYMMDD]")
    kb = pathlib.Path(sys.argv[1]).expanduser()
    kind = sys.argv[2]
    day = sys.argv[3] if len(sys.argv) > 3 else datetime.date.today().strftime("%Y%m%d")
    folder = kb / FOLDER[kind]
    nums = [int(m.group(1)) for p in folder.glob(f"{kind}-{day}-*.md")
            if (m := re.match(rf"{kind}-{day}-(\d+)", p.name))]
    print(f"{kind}-{day}-{max(nums, default=0) + 1:02d}")

if __name__ == "__main__":
    main()
