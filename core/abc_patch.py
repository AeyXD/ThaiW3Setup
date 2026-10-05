"""Small in-place edits of ActionScript 3 bytecode (DoABC tags) that keep every byte offset."""
from __future__ import annotations

DO_ABC = 82
OP_PUSHBYTE, OP_SETPROPERTY, OP_GETLEX, OP_GETPROPERTY = 0x24, 0x61, 0x60, 0x66


def _u30(d: bytes | bytearray, p: int) -> tuple[int, int]:
    v = shift = 0
    while True:
        b = d[p]
        p += 1
        v |= (b & 0x7F) << shift
        if not b & 0x80:
            return v, p
        shift += 7


def _multiname_names(d: bytes | bytearray, p: int) -> list[str | None]:
    """Names of the constant pool's multinames (None for runtime and generic ones); p points at the pool."""
    p += 4
    for _pool in ("int", "uint"):
        n, p = _u30(d, p)
        for _ in range(max(0, n - 1)):
            _, p = _u30(d, p)
    n, p = _u30(d, p)
    p += 8 * max(0, n - 1)
    n, p = _u30(d, p)
    strings = [""]
    for _ in range(max(0, n - 1)):
        ln, p = _u30(d, p)
        strings.append(bytes(d[p:p + ln]).decode("utf-8", "replace"))
        p += ln
    n, p = _u30(d, p)
    for _ in range(max(0, n - 1)):
        _, p = _u30(d, p + 1)
    n, p = _u30(d, p)
    for _ in range(max(0, n - 1)):
        count, p = _u30(d, p)
        for _ in range(count):
            _, p = _u30(d, p)
    n, p = _u30(d, p)
    names: list[str | None] = [None]
    for _ in range(max(0, n - 1)):
        kind = d[p]
        p += 1
        if kind in (0x07, 0x0D):
            _, p = _u30(d, p)
            name, p = _u30(d, p)
            names.append(strings[name])
        elif kind in (0x0F, 0x10):
            name, p = _u30(d, p)
            names.append(strings[name])
        elif kind in (0x11, 0x12):
            names.append(None)
        elif kind in (0x09, 0x0E):
            name, p = _u30(d, p)
            _, p = _u30(d, p)
            names.append(strings[name])
        elif kind in (0x1B, 0x1C):
            _, p = _u30(d, p)
            names.append(None)
        elif kind == 0x1D:
            _, p = _u30(d, p)
            count, p = _u30(d, p)
            for _ in range(count):
                _, p = _u30(d, p)
            names.append(None)
        else:
            raise ValueError(f"unknown multiname kind {kind:#x}")
    return names


def constant_sets(body: bytes | bytearray, abc_start: int, abc_end: int, prop: str) -> list[int]:
    """Offsets of the pushbyte operand in `<object>.prop = <byte constant>` inside one DoABC tag."""
    p = body.index(b"\0", abc_start + 4) + 1
    names = _multiname_names(body, p)
    targets = {i for i, name in enumerate(names) if name == prop}
    found = []
    for i in range(p, abc_end - 3):
        if body[i] != OP_SETPROPERTY or body[i - 2] != OP_PUSHBYTE:
            continue
        idx, _ = _u30(body, i + 1)
        if idx not in targets:
            continue
        # the object comes from getlex/getproperty right before the constant
        for back in range(3, 9):
            if body[i - back] in (OP_GETLEX, OP_GETPROPERTY) and _u30(body, i - back + 1)[1] == i - 2:
                found.append(i - 1)
                break
    return found
