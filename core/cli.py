"""Command-line interface: install / uninstall / status / detect."""
from __future__ import annotations

import argparse
import sys
from dataclasses import fields

from . import __version__
from .custom import cached_count, sheet_key
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
    sub.add_parser("custom", help="list custom translation sheets")
    sub.add_parser("check-update", help="check GitHub for a newer version of this setup")
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
    inst.add_argument("--sub-x", type=float, help="subtitle offset, percent of screen width")
    inst.add_argument("--sub-y", type=float, help="subtitle offset, percent of screen height")
    inst.add_argument("--sub-width", type=int, help="subtitle box width, percent of default (50-150)")
    inst.add_argument("--dialog-x", type=float, help="dialogue line offset, percent of screen width")
    inst.add_argument("--dialog-y", type=float, help="dialogue line offset, percent of screen height")
    inst.add_argument("--choice-x", type=float, help="dialogue choices offset, percent of screen width")
    inst.add_argument("--choice-y", type=float, help="dialogue choices offset, percent of screen height")
    inst.add_argument("--choice-scale", type=int, help="dialogue choices size, percent of default (50-250)")
    inst.add_argument("--custom", metavar="N,N", help="enable exactly these custom sheets (numbers from 'custom', 0 = none)")
    inst.add_argument("--refresh", action="store_true", help="force re-download of translations")
    inst.add_argument("--yes", action="store_true", help="remove old w3tu mods without asking")
    args = p.parse_args(argv)

    if args.cmd == "detect":
        for g in find_games():
            print(f"{g.path}  [{g.store or '-'}] {g.edition} {g.version}".rstrip())
            if g.stale_content:
                print(f"  ! leftover 4.x folders: {', '.join(g.stale_content)}")
        return 0
    if args.cmd == "check-update":
        from .update import check_for_update
        info = check_for_update()
        if info is None:
            print(f"up to date ({__version__})")
        else:
            print(f"new version {info.version} (current {__version__})\n{info.download_url}\n\n{info.notes}")
        return 0
    if args.cmd == "custom":
        for i, s in enumerate(load_options().custom_sheets, 1):
            count = cached_count(s["sheet_id"], s.get("tab") or "")
            print(f"{i}. [{'x' if s.get('enabled') else ' '}] {s.get('name', '')}  {sheet_key(s)}"
                  f"  ({count if count is not None else '-'} strings)")
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
                 "size1": args.size1, "size2": args.size2, "slot": args.slot,
                 "sub_x": args.sub_x, "sub_y": args.sub_y, "sub_width": args.sub_width,
                 "dialog_x": args.dialog_x, "dialog_y": args.dialog_y,
                 "choice_x": args.choice_x, "choice_y": args.choice_y, "choice_scale": args.choice_scale}
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
    if args.custom is not None:
        chosen = {int(n) for n in args.custom.split(",") if n.strip()}
        for i, s in enumerate(opts.custom_sheets, 1):
            s["enabled"] = i in chosen

    def confirm(message: str) -> bool:
        if args.yes:
            return True
        return input(message + " [y/N] ").strip().lower() in ("y", "yes")

    report = install(opts, _progress, confirm, force_download=args.refresh)
    save_options(opts)
    print(f"translated {report.translated}/{report.total} ({report.percent:.2f}%) from {report.source},"
          f" custom overrides {report.custom}")
    print("mods:", ", ".join(report.mods))
    for w in report.warnings:
        print("warning:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
