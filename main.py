"""Entry point: GUI by default, command line when arguments are given."""
import sys


def _attach_console() -> None:
    """Windows only: the windowed build starts without sys.stdout; reuse redirected handles or the parent console."""
    import ctypes
    import msvcrt
    import os

    kernel32 = ctypes.windll.kernel32
    kernel32.GetStdHandle.restype = ctypes.c_void_p
    streams = {}
    for name, std, mode in (("stdout", -11, "w"), ("stderr", -12, "w")):
        handle = kernel32.GetStdHandle(std)
        if handle and handle != ctypes.c_void_p(-1).value and kernel32.GetFileType(ctypes.c_void_p(handle)) in (1, 3):
            streams[name] = open(msvcrt.open_osfhandle(handle, os.O_WRONLY), mode, encoding="utf-8", buffering=1)
    if len(streams) < 2 and kernel32.AttachConsole(-1):
        console = open("CONOUT$", "w", encoding="utf-8", buffering=1)
        streams.setdefault("stdout", console)
        streams.setdefault("stderr", console)
        sys.stdin = open("CONIN$", encoding="utf-8")
    devnull = None
    for name in ("stdout", "stderr"):
        if name not in streams:
            devnull = devnull or open(os.devnull, "w", encoding="utf-8")
            streams[name] = devnull
    sys.stdout, sys.stderr = streams["stdout"], streams["stderr"]


def main() -> int:
    if len(sys.argv) > 1:
        if sys.stdout is None:
            if sys.platform == "win32":
                _attach_console()
            else:  # a macOS .app launched from Finder has no streams either, but no console to attach to
                import os
                sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        from core.cli import main as cli_main
        return cli_main()
    from gui.app import run
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
