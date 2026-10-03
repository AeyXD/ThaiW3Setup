"""The game folder the dev scripts read from. Set W3_GAME to point them at your own install."""
import os

GAME = os.environ.get("W3_GAME") or r"D:\SteamLibrary\steamapps\common\The Witcher 3"


def game_path(*parts: str) -> str:
    """A file inside the game folder, built with this platform's separator."""
    return os.path.join(GAME, *parts)
