#!/usr/bin/env python3
"""지식 베이스 초안을 대상 폴더에 복사하고 자리표시자를 치환한다.

사용: bootstrap.py <대상 폴더> --name <저장소 이름> --owner <소유자 표시 이름>
대상 폴더에 이미 파일이 있으면 그 파일은 건드리지 않는다. 플러그인은 기존 지식 베이스를 덮어쓰지 않는다.
초안에 파일이 없어도 스크립트가 쓰는 폴더(FOLDERS)는 빈 폴더로 만들어 둔다. git에 남도록 .gitkeep 을 넣는다.
"""
import argparse, datetime, pathlib, shutil, sys

# 스크립트가 파일을 적는 폴더. 초안에 없으면 만든다.
FOLDERS = [
    "raw/journal",    # 메모 (leave-memo)
    "raw/cases",      # 사례
    "raw/decisions",  # 결정
    "raw/context",    # 맥락
    "raw/sessions",   # 세션 발췌. 세션마다 파일 하나 (session_extract.py extract --save)
    "raw/reviews",    # 주 1회 점검 보고서
    "evolve",         # 추정 기록, 규칙별 사례표, 측정값 (analyze-context, measure.py)
    "wiki/projects",  # 프로젝트 카드
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--name", required=True)
    ap.add_argument("--owner", required=True)
    a = ap.parse_args()
    # 초안은 이 스킬 폴더의 assets/knowledge-base/ 에 있다 (scripts/ 의 한 단계 위가 스킬 폴더).
    src = pathlib.Path(__file__).resolve().parents[1] / "assets" / "knowledge-base"
    if not src.is_dir():
        sys.exit(f"초안 폴더가 없다: {src}")
    dst = pathlib.Path(a.target).expanduser().resolve()
    dst.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today()
    rep = {"{{REPO_NAME}}": a.name, "{{OWNER}}": a.owner,
           "{{DATE}}": today.strftime("%Y%m%d"), "{{DATE_ISO}}": today.isoformat()}
    created, skipped = [], []
    for p in sorted(src.rglob("*")):
        if p.is_dir():
            continue
        rel = str(p.relative_to(src))
        for k, v in rep.items():
            rel = rel.replace(k, v)
        out = dst / rel
        if out.exists():
            skipped.append(rel); continue
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            s = p.read_text(encoding="utf-8")
            for k, v in rep.items():
                s = s.replace(k, v)
            out.write_text(s, encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copy(p, out)
        created.append(rel)
    made = []
    for rel in FOLDERS:
        folder = dst / rel
        if folder.exists():
            continue
        folder.mkdir(parents=True)
        (folder / ".gitkeep").write_text("", encoding="utf-8")
        made.append(rel)
    print(f"만든 파일 {len(created)}개, 이미 있어서 건너뛴 파일 {len(skipped)}개"
          + (f", 만든 빈 폴더 {len(made)}개({', '.join(made)})" if made else ""))
    for r in skipped:
        print(f"  건너뜀: {r}")

if __name__ == "__main__":
    main()
