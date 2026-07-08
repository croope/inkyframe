"""
artwork.py — Art mode fallback.

When no photos are found in PHOTO_DIR the frame switches to displaying
public-domain paintings from ARTWORK_DIR (~/Artwork by default).

A simple last-shown file prevents the same painting from appearing twice
in a row even across restarts.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

import config

_STATE_FILE = Path("/home/chris/.photoframe_artwork.json")


def get_artwork() -> Optional[Path]:
    """
    Return a random artwork path from ARTWORK_DIR, or None if the folder
    does not exist or contains no supported images.

    Avoids repeating the most recently displayed artwork.
    """
    if not config.ARTWORK_DIR.exists():
        return None

    artworks: list[Path] = []
    for ext in config.SUPPORTED:
        artworks.extend(config.ARTWORK_DIR.rglob(f"*{ext}"))
        artworks.extend(config.ARTWORK_DIR.rglob(f"*{ext.upper()}"))

    artworks = list(set(artworks))
    if not artworks:
        return None

    last    = _load_last()
    choices = [a for a in artworks if str(a) != last] or artworks
    chosen  = random.choice(choices)

    _save_last(str(chosen))
    return chosen


def _load_last() -> str:
    try:
        return json.loads(_STATE_FILE.read_text()).get("last", "")
    except Exception:
        return ""


def _save_last(path: str) -> None:
    try:
        _STATE_FILE.write_text(json.dumps({"last": path}))
    except Exception:
        pass
