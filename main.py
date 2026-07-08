#!/usr/bin/env python3
"""
photoframe — a polished digital picture frame for the Pimoroni Inky Impression.

Usage
-----
    python3 main.py

Designed to be called by a systemd timer or cron job at whatever interval
you like (UPDATE_INTERVAL in config.py is a hint for the timer, not enforced
here).

File layout
-----------
    photoframe/
        main.py         ← this file
        config.py       ← all user-facing settings
        gallery.py      ← shuffled playlist management
        metadata.py     ← EXIF / GPS extraction, SQLite cache
        face_detect.py  ← OpenCV face detection (optional)
        layouts.py      ← layout engine and overlay drawing
        weather.py      ← OpenWeatherMap fetch + 1-hour cache
        artwork.py      ← art-mode fallback (~/Artwork)
"""

import sys
from pathlib import Path

# Allow running directly from the project directory without installation
sys.path.insert(0, str(Path(__file__).parent))

# Uncomment for HEIC / HEIF support (pip install pillow-heif):
# from pillow_heif import register_heif_opener
# register_heif_opener()

from PIL import Image, ImageEnhance, ImageOps

import artwork
import config
import gallery
import layouts
import metadata
import weather


# ---------------------------------------------------------------------------
# Image enhancement
# ---------------------------------------------------------------------------

def _enhance(img: Image.Image) -> Image.Image:
    """Gentle colour/contrast boost that suits e-paper's limited gamut."""
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.05)
    img = ImageEnhance.Sharpness(img).enhance(1.10)
    return img


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    # Initialise display first so we fail fast if the hardware isn't present
    from inky.auto import auto  # type: ignore
    display = auto()
    width   = display.width
    height  = display.height

    # Ensure the metadata cache table exists
    metadata.init_db()

    # -----------------------------------------------------------------------
    # Pick an image
    # -----------------------------------------------------------------------
    photo_path = gallery.next_photo()
    is_artwork = photo_path is None

    if is_artwork:
        photo_path = artwork.get_artwork()

    if photo_path is None:
        print(
            "No photos found in PHOTO_DIR and no artwork found in ARTWORK_DIR.\n"
            f"  PHOTO_DIR   = {config.PHOTO_DIR}\n"
            f"  ARTWORK_DIR = {config.ARTWORK_DIR}\n"
            "Add some images and try again."
        )
        sys.exit(1)

    print(f"Image : {photo_path}")

    # -----------------------------------------------------------------------
    # Load, orient, and enhance
    # -----------------------------------------------------------------------
    img = Image.open(photo_path)
    img = ImageOps.exif_transpose(img)   # correct camera rotation silently
    img = img.convert("RGB")
    img = _enhance(img)

    # -----------------------------------------------------------------------
    # Metadata (cached after the first run)
    # -----------------------------------------------------------------------
    meta = metadata.analyse(photo_path, img)

    print(
        f"Orient: {meta['orientation']}  "
        f"Faces: {meta['face_count']}  "
        f"Date: {meta.get('exif_date') or '—'}  "
        f"Location: {meta.get('location') or '—'}"
    )

    # -----------------------------------------------------------------------
    # Caption and weather
    # -----------------------------------------------------------------------
    if is_artwork:
        caption_text = photo_path.stem.replace("_", " ").title()
    else:
        caption_text = metadata.build_caption(meta)

    weather_text = weather.get_weather()

    # -----------------------------------------------------------------------
    # Render
    # -----------------------------------------------------------------------
    if is_artwork:
        final = layouts.artwork_layout(img, width, height, caption_text)
    else:
        final = layouts.render(img, meta, caption_text, weather_text, width, height)

    # -----------------------------------------------------------------------
    # Push to display
    # -----------------------------------------------------------------------
    display.set_image(final)
    display.show()

    print(f"Done.  Caption: {caption_text!r}")


if __name__ == "__main__":
    main()
