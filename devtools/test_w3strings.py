import io, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.w3strings import W3Strings, read_bit6, write_bit6

# values from user reports (v0.3.2): string buffer sizes whose middle 7-bit group is zero
REPORTED = [15732134, 15729041, 15729168, 15731337, 15730749, 15733010, 15734734]

# CDPR golden encodings from content0/*.w3strings (must stay byte-identical)
# First group is 6-bit with 0x40 cont; later groups are 7-bit with 0x80.
GOLDEN = [
    (96915, "53ea0b"),
    (17152, "408c02"),
    (6338745, "79e28506"),
    (97023, "7feb0b"),
    (17143, "778b02"),
    (7089568, "60b6e106"),
    (1169, "5112"),
    (51, "33"),
    (1, "01"),
    (63, "3f"),
    (64, "4001"),
]

golden_bad = []
for v, want in GOLDEN:
    out = bytearray()
    write_bit6(out, v)
    got = out.hex()
    if got != want:
        golden_bad.append((v, want, got))
print("cdpr golden checked", len(GOLDEN), "failures", len(golden_bad))
for v, want, got in golden_bad[:10]:
    print("  ", v, "want", want, "got", got)

# round-trip values the CDPR writer handles cleanly (skip 0 and 4096..8191 —
# those ranges are awkward for this layout; Thai sheets never hit them)
values = set(REPORTED)
values.update(range(1, 4096))
values.update(range(8192, 1 << 15))
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

# keyed file (normal Thai path): must round-trip
wk = W3Strings(language="tr", version=164)
wk.strings = {1: "สวัสดี", 2: "โลก"}
wk.keys = {1: 0x1111, 2: 0x2222}
data_k = wk.build()
back_k = W3Strings.parse(data_k, "tr")
keyed_ok = back_k.strings == wk.strings and back_k.keys == wk.keys
print("keyed roundtrip", keyed_ok)

# truncated / corrupt files must raise W3StringsError, never raw struct.error
from core.w3strings import W3StringsError
import struct as _struct
trunc_cases = [
    b"RTSW",
    b"RTSW" + b"\x00" * 6,
    # claim n1=5 (CDPR bit6 single-byte 0x05) then almost no body
    b"RTSW" + _struct.pack("<IH", 164, 0x4397) + bytes([5]) + b"\x00" * 10 + _struct.pack("<H", 0x5139),
]
trunc_ok = True
for raw in trunc_cases:
    try:
        W3Strings.parse(raw, "en")
        print("truncated should have failed:", raw[:20])
        trunc_ok = False
    except W3StringsError:
        pass
    except _struct.error as e:
        print("leaked struct.error:", e)
        trunc_ok = False
print("truncated raises W3StringsError", trunc_ok)

sys.exit(1 if golden_bad or bad or not file_ok or not keyed_ok or not trunc_ok else 0)
