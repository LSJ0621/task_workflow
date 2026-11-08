#!/usr/bin/env python3
"""지식 베이스 위치를 Claude Code 사용자 설정(~/.claude/settings.json)의 env 에 저장한다.

사용: save_setting.py --dir <절대 경로> [--repo <원격 저장소 주소>]
기존 설정은 보존하고 두 키만 더하거나 바꾼다. 환경 변수로 두는 이유: 모든 세션·서브에이전트·명령에서
$KNOWLEDGE_BASE_DIR 로 바로 보이기 때문이다.
"""
import argparse, json, pathlib

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--repo")
    ap.add_argument("--settings", default="~/.claude/settings.json")
    a = ap.parse_args()
    path = pathlib.Path(a.settings).expanduser()
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    env = data.setdefault("env", {})
    env["KNOWLEDGE_BASE_DIR"] = str(pathlib.Path(a.dir).expanduser().resolve())
    if a.repo:
        env["KNOWLEDGE_BASE_REPO"] = a.repo
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"저장됨: KNOWLEDGE_BASE_DIR={env['KNOWLEDGE_BASE_DIR']}" + (f", KNOWLEDGE_BASE_REPO={a.repo}" if a.repo else ""))

if __name__ == "__main__":
    main()
