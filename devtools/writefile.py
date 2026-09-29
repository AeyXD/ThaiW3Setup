import sys
from pathlib import Path
p = Path(sys.argv[1])
p.parent.mkdir(parents=True, exist_ok=True)
data = sys.stdin.buffer.read().decode("utf-8")
if data.startswith("\ufeff"):
    data = data[1:]
p.write_text(data.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
print(f"wrote {p} ({len(data)} chars, thai={sum(1 for c in data if 0xE00 <= ord(c) <= 0xE7F)})")
