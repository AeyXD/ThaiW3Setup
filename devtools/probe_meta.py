import struct, sys


class R:
    def __init__(self, d):
        self.d = d
        self.p = 0

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.p)[0]
        self.p += 4
        return v

    def vlq(self):
        b1 = self.d[self.p]; self.p += 1
        sign = b1 & 128
        nxt = b1 & 64
        size = b1 & 63
        off = 6
        while nxt:
            b = self.d[self.p]; self.p += 1
            size |= (b & 127) << off
            nxt = b & 128
            off += 7
        return -size if sign else size

    def take(self, n):
        v = self.d[self.p:self.p + n]
        self.p += n
        return v


def arr(r, name, width, show=3):
    n = r.vlq()
    start = r.p
    items = [struct.unpack_from("<" + "I" * (width // 4), r.d, r.p + i * width) for i in range(min(n, show))]
    r.p += n * width
    print(f"  {name}: count={n} width={width} at={start} sample={items}")
    return n


def probe(p, widths):
    d = open(p, "rb").read()
    r = R(d)
    magic = r.take(4); ver = r.u32(); a = r.u32(); b = r.u32()
    st = r.vlq()
    print(p, "ver", ver, "maxs", a, b, "strtab", st, "len", len(d))
    r.p += st
    for name, w in widths:
        arr(r, name, w)
    print("  end at", r.p, "of", len(d), "remaining", len(d) - r.p, d[r.p:r.p + 48].hex())


V6 = [("fileInfo", 32), ("fileEntry", 20), ("bundleInfo", 24), ("buffers", 4), ("dirInit", 8), ("fileInit", 12), ("hashes", 16)]

if __name__ == "__main__":
    for p in sys.argv[1:]:
        probe(p, V6)
