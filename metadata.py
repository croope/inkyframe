"""
metadata.py — Image analysis and caching.

The first time an image is seen its metadata is extracted and stored in a
small SQLite database so that subsequent updates are instant.  Stored data:

  • orientation  (landscape / portrait / panorama / square)
  • aspect ratio
  • EXIF date
  • GPS coordinates → human-readable location name
  • face count and bounding rectangles
  • favourite flag (can be set externally)
"""

from __future__ import annotations

import json
import sqlite3
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import ExifTags, Image

import config


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create the cache table if it does not already exist."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS image_cache (
                path         TEXT    PRIMARY KEY,
                mtime        REAL    NOT NULL,
                orientation  TEXT    NOT NULL,
                aspect_ratio REAL    NOT NULL,
                face_count   INTEGER NOT NULL DEFAULT 0,
                face_rects   TEXT    NOT NULL DEFAULT '[]',
                exif_date    TEXT,
                gps_lat      REAL,
                gps_lon      REAL,
                location     TEXT,
                is_favourite INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _read_cache(path: Path) -> Optional[dict]:
    mtime = path.stat().st_mtime
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM image_cache WHERE path = ? AND mtime = ?",
            (str(path), mtime),
        ).fetchone()
    if row:
        d = dict(row)
        d["face_rects"] = json.loads(d["face_rects"])
        return d
    return None


def _write_cache(data: dict) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO image_cache
                (path, mtime, orientation, aspect_ratio, face_count, face_rects,
                 exif_date, gps_lat, gps_lon, location, is_favourite)
            VALUES
                (:path, :mtime, :orientation, :aspect_ratio, :face_count,
                 :face_rects, :exif_date, :gps_lat, :gps_lon, :location,
                 :is_favourite)
            """,
            data,
        )
        conn.commit()


# ---------------------------------------------------------------------------
# EXIF helpers
# ---------------------------------------------------------------------------

def _exif_date(img: Image.Image) -> Optional[str]:
    try:
        exif = img.getexif()
        for tag, value in exif.items():
            if ExifTags.TAGS.get(tag) == "DateTimeOriginal":
                dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                return dt.strftime("%d %b %Y")
    except Exception:
        pass
    return None


def _exif_gps(img: Image.Image) -> Tuple[Optional[float], Optional[float]]:
    try:
        exif = img.getexif()
        gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
        if not gps_ifd:
            return None, None

        def _dms(dms, ref: str) -> float:
            d, m, s = dms
            dd = float(d) + float(m) / 60 + float(s) / 3600
            if ref in ("S", "W"):
                dd = -dd
            return dd

        lat = _dms(gps_ifd[2], gps_ifd[1])
        lon = _dms(gps_ifd[4], gps_ifd[3])
        return lat, lon
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Reverse geocoding
# ---------------------------------------------------------------------------

def _reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """
    Return a human-readable place name for (lat, lon).

    Tries the offline ``reverse_geocoder`` package first (fast, no internet
    required).  Falls back to the Nominatim API (requires internet access).
    Returns None if neither method succeeds.
    """
    # --- offline via reverse_geocoder package ---
    try:
        import reverse_geocoder as rg  # type: ignore
        results = rg.search((lat, lon), verbose=False)
        if results:
            r = results[0]
            return r.get("name") or r.get("admin1") or r.get("cc")
    except ImportError:
        pass

    # --- online via Nominatim (rate-limited, no API key needed) ---
    try:
        url = (
            "https://nominatim.openstreetmap.org/reverse"
            f"?lat={lat}&lon={lon}&format=json&zoom=10"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "photoframe/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        addr = data.get("address", {})
        return (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("county")
            or addr.get("state")
        )
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Orientation
# ---------------------------------------------------------------------------

def _orientation(img: Image.Image) -> Tuple[str, float]:
    w, h = img.size
    ratio = w / h
    if ratio >= 1.8:
        return "panorama", ratio
    elif ratio > 1.05:
        return "landscape", ratio
    elif ratio < 0.95:
        return "portrait", ratio
    else:
        return "square", ratio


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyse(path: Path, img: Image.Image) -> dict:
    """
    Return a metadata dict for *path* / *img*.

    Results are cached in the SQLite database keyed on the file path and
    mtime, so repeated calls are essentially free.
    """
    cached = _read_cache(path)
    if cached:
        return cached

    mtime                   = path.stat().st_mtime
    orientation, aspect_ratio = _orientation(img)
    exif_date               = _exif_date(img)
    gps_lat, gps_lon        = _exif_gps(img)

    location: Optional[str] = None
    if gps_lat is not None and gps_lon is not None:
        location = _reverse_geocode(gps_lat, gps_lon)

    face_count = 0
    face_rects: List = []
    if config.FACE_DETECTION:
        try:
            from face_detect import detect_faces
            face_rects = detect_faces(img)
            face_count = len(face_rects)
        except Exception:
            pass

    data = {
        "path":         str(path),
        "mtime":        mtime,
        "orientation":  orientation,
        "aspect_ratio": aspect_ratio,
        "face_count":   face_count,
        "face_rects":   json.dumps(face_rects),
        "exif_date":    exif_date,
        "gps_lat":      gps_lat,
        "gps_lon":      gps_lon,
        "location":     location,
        "is_favourite": 0,
    }
    _write_cache(data)

    data["face_rects"] = face_rects
    return data


def build_caption(meta: dict) -> str:
    """
    Compose the display caption from a metadata dict.

    Shows location and/or date according to config, falling back to the
    filename stem if nothing else is available.
    """
    parts = []
    if config.SHOW_LOCATION and meta.get("location"):
        parts.append(meta["location"])
    if config.SHOW_DATE and meta.get("exif_date"):
        parts.append(meta["exif_date"])
    if not parts and config.SHOW_FILENAME:
        parts.append(Path(meta["path"]).stem)
    return "  •  ".join(parts)
