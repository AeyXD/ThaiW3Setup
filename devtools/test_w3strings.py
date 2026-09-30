import io, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.w3strings import W3Strings, read_bit6, write_bit6

# values from user reports (v0.3.2): string buffer sizes whose middle 7-bit group is zero
REPORTED = [15732134, 15729041, 15729168, 15731337, 15730749, 15733010, 15734734]

values = set(REPORTED)
# read_bit6 misreads two-byte values 4096..8191; real counts and buffer sizes are far larger
values.update(range(1, 1 << 12))
values.update(range(1 << 13, 1 << 15))
for base in (1 << 20, 15 << 20, 1 << 27):
    values.update(range(base - 300, base + 300))
values.update(range(15 << 20, (15 << 20) + (1 << 13), 7))

bad = []
for v in sorted(values):
    out = bytearray()
    try:
        write_bit6(out, v)
        got = read_bit6(io.BytesIO(bytes(out) + b"\xff"))
    except Exception as e:
        bad.append((v, repr(e)))
        continue
    if got != v:
        bad.append((v, f"read back {got} from {out.hex()}"))

print("bit6 values checked", len(values), "failures", len(bad))
for v, why in bad[:10]:
    print("  ", v, why)

# a whole file whose string buffer length lands in the reported range
w = W3Strings(language="tr", version=164)
w.strings[1] = "a" * (REPORTED[1] - 1)
w.keys[1] = 0x1234
data = w.build()
back = W3Strings.parse(data, "tr")
file_ok = back.strings == w.strings and back.keys == w.keys
print("file roundtrip", file_ok)

sys.exit(1 if bad or not file_ok else 0)
