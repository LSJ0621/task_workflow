#!/usr/bin/env python3
"""지식 베이스 초안을 대상 폴더에 복사하고 자리표시자를 치환한다.

사용: bootstrap.py <대상 폴더> --name <저장소 이름> --owner <소유자 표시 이름>
대상 폴더에 이미 파일이 있으면 그 파일은 건드리지 않는다. 플러그인은 기존 지식 베이스를 덮어쓰지 않는다.
"""
import argparse, datetime, pathlib, shutil, sys

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
    print(f"만든 파일 {len(created)}개, 이미 있어서 건너뛴 파일 {len(skipped)}개")
    for r in skipped:
        print(f"  건너뜀: {r}")

if __name__ == "__main__":
    main()
