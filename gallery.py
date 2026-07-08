"""
gallery.py — Playlist management.

Shuffles photos into a playlist, persists the position across restarts,
and keeps a short recent-history window so the same image or a run of
very similar images doesn't appear twice in close succession.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List, Tuple

import config


def get_images() -> List[Path]:
    """Return every supported image under PHOTO_DIR, sorted for stability."""
    images: List[Path] = []
    for ext in config.SUPPORTED:
        images.extend(config.PHOTO_DIR.rglob(f"*{ext}"))
        images.extend(config.PHOTO_DIR.rglob(f"*{ext.upper()}"))
    # deduplicate (case-insensitive filesystems can produce duplicates)
    return sorted(set(images))


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def _load_state() -> Tuple[List[Path], int, List[str]]:
    try:
        if config.STATE_FILE.exists():
            data = json.loads(config.STATE_FILE.read_text())
            playlist = [Path(p) for p in data.get("playlist", [])]
            index    = int(data.get("index", 0))
            recent   = data.get("recent", [])
            # Remove stale paths
            playlist = [p for p in playlist if p.exists()]
            if playlist:
                return playlist, index, recent
    except Exception:
        pass
    return [], 0, []


def _save_state(playlist: List[Path], index: int, recent: List[str]) -> None:
    try:
        config.STATE_FILE.write_text(
            json.dumps({
                "playlist": [str(p) for p in playlist],
                "index":    index,
                "recent":   recent,
            })
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def next_photo() -> Path | None:
    """
    Return the next photo path from the shuffled playlist, or None if the
    photo directory is empty.

    The playlist is rebuilt (reshuffled) each time it is exhausted.  The
    last RECENT_WINDOW paths are remembered so that the reshuffle doesn't
    immediately repeat the final image.
    """
    images = get_images()
    if not images:
        return None

    playlist, index, recent = _load_state()

    # Rebuild when exhausted or the saved playlist no longer matches disk
    if index >= len(playlist) or not playlist:
        shuffled = images[:]
        random.shuffle(shuffled)
        # Make sure the very first image of the new cycle isn't the same as
        # the last image of the previous cycle
        if recent and shuffled and str(shuffled[0]) == recent[-1]:
            random.shuffle(shuffled)
        playlist = shuffled
        index    = 0

    photo = playlist[index]

    # Update recent window
    recent.append(str(photo))
    if len(recent) > config.RECENT_WINDOW:
        recent = recent[-config.RECENT_WINDOW:]

    _save_state(playlist, index + 1, recent)
    return photo
