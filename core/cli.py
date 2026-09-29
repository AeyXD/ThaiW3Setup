"""Command-line interface: install / uninstall / status / detect."""
from __future__ import annotations

import argparse
import sys
from dataclasses import fields

from . import __version__
from .game_detect import find_games, identify
from .installer import install, status, uninstall
from .options import FONTS, InstallOptions, load_options, save_options


def _progress(fraction: float, message: str) -> None:
    print(f"[{fraction * 100:5.1f}%] {message}", flush=True)


def _game_path(arg: str | None) -> str:
    if arg:
        return arg
    games = [g for g in find_games() if g.supported]
    if not games:
        sys.exit("Witcher 3 Remastered not found, pass --game PATH")
    return str(games[0].path)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ThaiW3Setup", description="Thai translation for The Witcher 3 Remastered")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("detect")
    for name in ("install", "uninstall", "status"):
        s = sub.add_parser(name)
        s.add_argument("--game")
    inst = sub.choices["install"]
    inst.add_argument("--font", choices=list(FONTS))
    inst.add_argument("--mode", choices=["thai", "double"])
    inst.add_argument("--english-first", action="store_true")
    inst.add_argument("--color1")
    inst.add_argument("--color2")
    inst.add_argument("--size1", type=int)
    inst.add_argument("--size2", type=int)
    inst.add_argument("--no-speaker-colors", action="store_true")
    inst.add_argument("--no-storybook", action="store_true")
    inst.add_argument("--no-subtitle-style", action="store_true")
    inst.add_argument("--slot", choices=["tr", "en"])
    inst.add_argument("--refresh", action="store_true", help="force re-download of translations")
    inst.add_argument("--yes", action="store_true", help="remove old w3tu mods without asking")
    args = p.parse_args(argv)

    if args.cmd == "detect":
        for g in find_games():
            print(f"{g.path}  [{g.store or '-'}] {g.edition}")
        return 0

    game_path = _game_path(args.game)
    if args.cmd == "status":
        st = status(identify(game_path))
        for f in fields(st):
            print(f"{f.name}: {getattr(st, f.name)}")
        return 0
    if args.cmd == "uninstall":
        print("removed:", ", ".join(uninstall(game_path)) or "-")
        return 0

    opts = load_options()
    opts.game_path = game_path
    overrides = {"font": args.font, "mode": args.mode, "color1": args.color1, "color2": args.color2,
                 "size1": args.size1, "size2": args.size2, "slot": args.slot}
    for key, value in overrides.items():
        if value is not None:
            setattr(opts, key, value)
    if args.english_first:
        opts.thai_first = False
    if args.no_speaker_colors:
        opts.speaker_colors = False
    if args.no_storybook:
        opts.storybook = False
    if args.no_subtitle_style:
        opts.subtitle_style = False

    def confirm(message: str) -> bool:
        if args.yes:
            return True
        return input(message + " [y/N] ").strip().lower() in ("y", "yes")

    report = install(opts, _progress, confirm, force_download=args.refresh)
    save_options(opts)
    print(f"translated {report.translated}/{report.total} ({report.percent:.2f}%) from {report.source}")
    print("mods:", ", ".join(report.mods))
    for w in report.warnings:
        print("warning:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
