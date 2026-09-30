"""Problem report: game version, installed mods, conflicts and mods.settings, sent to the report Worker."""
from __future__ import annotations

import ctypes
import getpass
import json
import os
import platform
import re
import urllib.request
from datetime import datetime
from pathlib import Path

from . import __version__
from .game_detect import EDITION_UNKNOWN, GameInfo, identify
from .installer import MOD_TEXT, OUR_MODS, THAI_CHARS, legacy_mods, status
from .paths import app_data_dir
from .w3strings import W3Strings

# Cloudflare Worker in worker/; THAIW3_REPORT_URL overrides it for testing
REPORT_URL = "https://thaiw3setup-report.owltoool.workers.dev/report"
MAGIC = "ThaiW3Setup report"
MAX_BYTES = 200 * 1024
LOG_LINES = 80
STRING_LANGS = ("tr", "en")


def report_url() -> str:
    return os.environ.get("THAIW3_REPORT_URL") or REPORT_URL


def _content_dirs(game: GameInfo) -> list[str]:
    content = game.path / "content"
    out = []
    for d in sorted(content.iterdir(), key=lambda d: (not d.is_dir(), int(re.sub(r"\D", "", d.name) or 0), d.name)):
        if d.is_dir():
            n = sum(1 for f in d.rglob("*") if f.is_file()) if d.name != "content0" else len(list(d.iterdir()))
            out.append(f"{d.name}/: {n} {'entries' if d.name == 'content0' else 'files'}")
        else:
            out.append(f"{d.name}: {d.stat().st_size} bytes")
    return out


def _launcher_config(game: GameInfo) -> str:
    try:
        return re.sub(r"\s+", " ", (game.path / "launcher-configuration.json").read_text(encoding="utf-8-sig"))[:600]
    except FileNotFoundError:
        return "(not found)"
    except OSError as exc:
        return f"(unreadable: {exc})"


def documents_dir() -> Path:
    try:
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:
            return Path(buf.value)
    except (AttributeError, OSError):
        pass
    return Path.home() / "Documents"


def _mods_settings_paths() -> list[Path]:
    paths = [documents_dir() / "The Witcher 3" / "mods.settings",
             Path.home() / "Documents" / "The Witcher 3" / "mods.settings",
             Path.home() / "OneDrive" / "Documents" / "The Witcher 3" / "mods.settings"]
    out: list[Path] = []
    for p in paths:
        if p not in out:
            out.append(p)
    return out


def _has_thai(path: Path, language: str) -> bool | None:
    try:
        sample = list(W3Strings.load(path, language).strings.values())[:3000]
    except Exception:
        return None
    return sum(1 for s in sample if THAI_CHARS.search(s)) > 100


def _describe_mod(path: Path) -> str:
    files = [f for f in path.rglob("*") if f.is_file()]
    notable = sorted({f.name.lower() for f in files if f.suffix.lower() in (".w3strings", ".redswf")})
    scripts = sum(1 for f in files if f.suffix.lower() == ".ws")
    bundles = sum(1 for f in files if f.suffix.lower() == ".bundle")
    parts = [f"{len(files)} files"]
    if scripts:
        parts.append(f"{scripts} scripts")
    if bundles:
        parts.append(f"{bundles} bundles")
    if notable:
        parts.append(", ".join(notable[:12]))
    return "; ".join(parts)


def _conflicts(game: GameInfo) -> list[str]:
    out = [f"leftover 4.x folders: {', '.join(game.stale_content)}"] if game.stale_content else []
    for p in legacy_mods(game):
        out.append(f"old w3tu Thai mod: mods\\{p.name}")
    if game.mods_dir.is_dir():
        for mod in sorted(game.mods_dir.iterdir()):
            if not mod.is_dir() or mod.name in OUR_MODS:
                continue
            for lang in STRING_LANGS:
                if list(mod.rglob(f"{lang}.w3strings")):
                    out.append(f"mods\\{mod.name} has {lang}.w3strings (overrides {MOD_TEXT})")
            fonts = [f.name for f in mod.rglob("*") if f.is_file() and "font" in f.name.lower()]
            if fonts:
                out.append(f"mods\\{mod.name} has font files: {', '.join(sorted(set(fonts))[:6])}")
    for lang in STRING_LANGS:
        for f in game.strings_files(lang):
            if f.parent.name == "content0" and _has_thai(f, lang):
                out.append(f"game file {f.relative_to(game.path)} contains Thai (modified by an old tool)")
    return out


def _redact(text: str) -> str:
    home = str(Path.home())
    text = re.sub(re.escape(home), "%USERPROFILE%", text, flags=re.IGNORECASE)
    try:
        user = getpass.getuser()
    except Exception:
        user = ""
    if len(user) >= 3:
        text = re.sub(rf"(?<![A-Za-z0-9]){re.escape(user)}(?![A-Za-z0-9])", "<user>", text, flags=re.IGNORECASE)
    return text


def _options_summary(options: dict | None) -> str:
    if not options:
        return "-"
    short = {k: v for k, v in options.items() if k not in ("custom_sheets", "known_default_sheets", "game_path")}
    sheets = [s.get("name") or s.get("sheet_id", "") for s in options.get("custom_sheets", []) if s.get("enabled")]
    return f"{json.dumps(short, ensure_ascii=False)}\ncustom sheets enabled: {', '.join(sheets) or '-'}"


def _log_tail(path: Path, lines: int) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return "(no log)"


def build_report(game_path: str, note: str = "") -> str:
    game = identify(game_path) if game_path else None
    lines = [MAGIC,
             f"app: {__version__}",
             f"created: {datetime.now().astimezone().isoformat(timespec='seconds')}",
             f"windows: {platform.platform()}",
             f"documents: {documents_dir()}"]
    if note.strip():
        lines += ["", "[user note]", note.strip()]
    lines.append("")
    if game is None:
        lines.append("game: (no folder selected)")
    else:
        lines += [f"game path: {game.path}",
                  f"game edition: {game.edition} {game.store}".rstrip(),
                  f"game version: {game.version or '(unknown)'}"]
        if game.edition != EDITION_UNKNOWN:
            lines += ["", "[content]"] + _content_dirs(game)
            lines += [f"launcher-configuration.json: {_launcher_config(game)}"]
        st = status(game)
        lines += ["", "[install status]",
                  f"installed: {st.installed}  version: {st.version}  at: {st.installed_at}  percent: {st.percent:.2f}",
                  f"our mods: {', '.join(st.mods) or '-'}",
                  f"options: {_options_summary(st.options)}"]
        lines += ["", "[conflicts]"] + (_conflicts(game) or ["none found"])
        lines += ["", "[mods]"]
        if game.mods_dir.is_dir():
            lines += [f"{m.name}: {_describe_mod(m)}" for m in sorted(game.mods_dir.iterdir()) if m.is_dir()] or ["(empty)"]
        else:
            lines.append("(no mods folder)")
        dlc = game.path / "dlc"
        lines += ["", "[dlc]", ", ".join(sorted(d.name for d in dlc.iterdir() if d.is_dir())) if dlc.is_dir() else "(none)"]
    for path in _mods_settings_paths():
        lines += ["", f"[mods.settings] {path}"]
        try:
            lines.append(path.read_text(encoding="utf-8", errors="replace").strip() or "(empty)")
        except FileNotFoundError:
            lines.append("(not found)")
        except OSError as exc:
            lines.append(f"(unreadable: {exc})")
    lines += ["", "[install.log]", _log_tail(app_data_dir() / "install.log", LOG_LINES)]
    text = _redact("\n".join(lines))
    data = text.encode("utf-8")
    if len(data) > MAX_BYTES:
        text = data[:MAX_BYTES].decode("utf-8", errors="ignore") + "\n(truncated)"
    return text


def send_report(text: str, timeout: float = 30) -> str:
    """Upload the report; returns the id the Worker assigned."""
    url = report_url()
    if not url:
        raise RuntimeError("report server not configured")
    req = urllib.request.Request(url, data=text.encode("utf-8"), method="POST", headers={
        "Content-Type": "text/plain; charset=utf-8", "User-Agent": f"ThaiW3Setup/{__version__}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))["id"]
