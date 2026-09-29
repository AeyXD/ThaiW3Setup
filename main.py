"""Entry point: GUI by default, command line when arguments are given."""
import sys


def main() -> int:
    if len(sys.argv) > 1:
        if sys.stdout is None:  # windowed build has no console of its own
            import ctypes
            import os
            if ctypes.windll.kernel32.AttachConsole(-1):
                sys.stdout = sys.stderr = open("CONOUT$", "w", encoding="utf-8")
                sys.stdin = open("CONIN$", encoding="utf-8")
            else:
                sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")
        from core.cli import main as cli_main
        return cli_main()
    from gui.app import run
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
