"""Write Thai release notes (shown on GitHub and in the in-app update dialog).

usage: python packaging/release_notes.py VERSION SHA256 OUT [VIRUSTOTAL_ANALYSIS]
"""
import re
import subprocess
import sys

KINDS = {"feat": "เพิ่ม", "fix": "แก้ไข", "perf": "ปรับปรุง", "refactor": "ปรับปรุง", "docs": "เอกสาร"}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8").stdout.strip()


def changes() -> list[str]:
    tags = git("tag", "--sort=-creatordate", "--merged", "HEAD").splitlines()
    head_tags = set(git("tag", "--points-at", "HEAD").splitlines())
    previous = next((t for t in tags if t not in head_tags), "")
    log_range = f"{previous}..HEAD" if previous else "HEAD"
    out = []
    for subject in git("log", log_range, "--no-merges", "--pretty=%s").splitlines():
        m = re.match(r"(\w+)(\([^)]*\))?!?:\s*(.+)", subject)
        if not m:
            out.append(f"- {subject}")
        elif m.group(1) in KINDS:
            out.append(f"- {KINDS[m.group(1)]}: {m.group(3)}")
    return out


def main() -> None:
    version, sha256, path = sys.argv[1:4]
    analysis = sys.argv[4] if len(sys.argv) > 4 else ""
    lines = [f"## ThaiW3Setup {version}", ""]
    items = changes()
    if items:
        lines += ["### สิ่งที่เปลี่ยน", *items, ""]
    lines += [
        "### วิธีติดตั้ง / อัปเดต",
        f"1. ดาวน์โหลด `ThaiW3Setup-{version}.zip` แล้วแตกไฟล์ทั้งโฟลเดอร์",
        "   (แตกทับโฟลเดอร์เดิมได้ ค่าที่ตั้งไว้ไม่หาย)",
        "2. เปิด `ThaiW3Setup.exe` แล้วกด **ติดตั้ง / อัปเดต**",
        "3. ถ้า Windows ขึ้น \"Windows protected your PC\" ให้กด **More info** > **Run anyway**",
        "",
        f"SHA256: `{sha256}`",
    ]
    if analysis:
        lines += ["", "ผลสแกน VirusTotal:"]
        for item in analysis.split(","):
            name, _, url = item.partition("=")
            lines.append(f"- [{name.replace(chr(92), '/').split('/')[-1]}]({url})")
    lines += ["", f"build โดย GitHub Actions จาก commit {git('rev-parse', '--short', 'HEAD')}"]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
