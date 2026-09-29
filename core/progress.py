from __future__ import annotations

from typing import Callable

ProgressFn = Callable[[float, str], None]


def noop(_fraction: float, _message: str) -> None:
    pass


def scaled(progress: ProgressFn, start: float, end: float) -> ProgressFn:
    """Map a sub-task's 0..1 progress onto [start, end] of the parent."""
    def inner(fraction: float, message: str) -> None:
        progress(start + (end - start) * max(0.0, min(1.0, fraction)), message)
    return inner
