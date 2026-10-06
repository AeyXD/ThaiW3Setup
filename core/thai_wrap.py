"""Thai word segmentation: marks word boundaries so Scaleform can wrap lines inside Thai runs.

Scaleform only wraps at Unicode spaces and Thai has none between words. A hair space (U+200A)
is a space to Scaleform, and the installed fonts get a zero-width glyph for it, so it adds a
line-break opportunity without moving any text.
"""
from __future__ import annotations

import gzip
import re
from functools import lru_cache

from .paths import assets_dir

BREAK = "\u200a"
WORDS_FILE = "thai_words.txt.gz"  # union: pythainlp corpus (Apache-2.0) + ICU thaidict (Unicode License) — ที่มาดูหัวไฟล์ข้างใน

THAI_RUN = re.compile("[\u0e01-\u0e4e]+")
# a cluster never starts with a following vowel, upper/lower vowel, tone mark or repetition mark
NO_BREAK_BEFORE = frozenset("\u0e2f\u0e30\u0e31\u0e32\u0e33\u0e34\u0e35\u0e36\u0e37\u0e38\u0e39\u0e3a"
                            "\u0e45\u0e46\u0e47\u0e48\u0e49\u0e4a\u0e4b\u0e4c\u0e4d\u0e4e")
# leading vowels belong to the consonant after them
NO_BREAK_AFTER = frozenset("\u0e40\u0e41\u0e42\u0e43\u0e44")
SHORT_WORD = 2
_END = ""


def load_words() -> set[str]:
    with gzip.open(assets_dir() / WORDS_FILE, "rt", encoding="utf-8") as fh:
        return {w for w in (line.strip() for line in fh) if w and not w.startswith("#")}


class ThaiWrapper:
    def __init__(self, words):
        self.trie: dict = {}
        self._split = lru_cache(maxsize=200_000)(self._split_run)
        self.add_words(words)

    def add_words(self, words) -> None:
        for w in words:
            node = self.trie
            for c in w:
                node = node.setdefault(c, {})
            node[_END] = True
        self._split.cache_clear()

    def wrap(self, text: str) -> str:
        if not THAI_RUN.search(text):
            return text
        return THAI_RUN.sub(lambda m: BREAK.join(self._split(m.group())), text)

    def _split_run(self, run: str) -> tuple[str, ...]:
        n = len(run)
        ok = [i == 0 or i == n or (run[i] not in NO_BREAK_BEFORE and run[i - 1] not in NO_BREAK_AFTER)
              for i in range(n + 1)]
        # best[i] = (unknown chars, words) for run[:i]; prev[i] = (start, is_word)
        inf = (n + 1, n + 1)
        best = [inf] * (n + 1)
        prev = [(0, False)] * (n + 1)
        best[0] = (0, 0)
        for i in range(n):
            if best[i] == inf or not ok[i]:
                continue
            unknown, count = best[i]
            node, j = self.trie, i
            while j < n and run[j] in node:
                node = node[run[j]]
                j += 1
                if _END in node and ok[j] and (unknown, count + 1) < best[j]:
                    best[j], prev[j] = (unknown, count + 1), (i, True)
            j = i + 1
            while not ok[j]:
                j += 1
            if (unknown + j - i, count + 1) < best[j]:
                best[j], prev[j] = (unknown + j - i, count + 1), (i, False)
        parts: list[tuple[str, bool]] = []
        j = n
        while j > 0:
            i, word = prev[j]
            parts.append((run[i:j], word))
            j = i
        parts.reverse()
        # unknown text stays in one piece, together with tiny words stuck to it (ท|ริ|สส์ -> ทริสส์)
        merged: list[list] = []
        for k, (text, word) in enumerate(parts):
            near_unknown = (k > 0 and not parts[k - 1][1]) or (k + 1 < len(parts) and not parts[k + 1][1])
            unknown = not word or (len(text) <= SHORT_WORD and near_unknown)
            if merged and unknown and not merged[-1][1]:
                merged[-1][0] += text
            else:
                merged.append([text, not unknown])
        return tuple(text for text, _ in merged)
