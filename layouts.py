"""
layouts.py — Layout engine.

Chooses the right display style for each image and composites the final
PIL Image that is pushed to the Inky Impression.

Layout selection matrix
-----------------------
Orientation  STYLE setting   Result
-----------  -------------   ------
panorama     any             Letterboxed elegantly; bars filled with bg colour
portrait     any             Blurred copy fills screen; sharp photo centred
                             (BLUR_PORTRAITS=False → gallery mount instead)
landscape    "gallery"       Classic mount with a thin border
landscape    "auto"          Near-full-screen, thin side mounts; face-aware
square       any             Gallery mount

Overlays (all optional):
  • Caption   — location  •  date (bottom-left)
  • Weather   — bottom-right, same line as caption
  • Clock     — top-right, small
  • Paper texture — subtle noise on the background (requires numpy)

Day / night theme:
  • Day   → cream  background, warm-grey caption
  • Night → charcoal background, light-grey caption
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import List, Optional, Tuple

from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps,
)

import config

# ---------------------------------------------------------------------------
# Colour palettes
# ---------------------------------------------------------------------------

_CREAM          = (248, 245, 238)
_CHARCOAL       = (42,  40,  38)
_CAPTION_WARM   = (90,  85,  78)   # on cream background
_CAPTION_LIGHT  = (200, 195, 188)  # on charcoal background
_BORDER_DAY     = (160, 155, 148)
_BORDER_NIGHT   = (80,  78,  75)

# ---------------------------------------------------------------------------
# Day / night helpers
# ---------------------------------------------------------------------------

def _is_night() -> bool:
    if config.DAY_NIGHT == "day":
        return False
    if config.DAY_NIGHT == "night":
        return True
    # Auto mode — use a simple sunrise/sunset calculation
    now   = datetime.now()
    hour  = now.hour + now.minute / 60
    try:
        rise, set_ = _sun_times(config.LATITUDE, config.LONGITUDE, now)
    except Exception:
        rise, set_ = 6.5, 20.5
    return hour < rise or hour > set_


def _sun_times(lat: float, lon: float, dt: datetime) -> Tuple[float, float]:
    """Approximate civil sunrise/sunset in decimal hours (local solar time)."""
    doy = dt.timetuple().tm_yday
    B   = math.radians((360 / 365) * (doy - 81))
    lat_r = math.radians(lat)
    decl  = math.radians(23.45 * math.sin(B))
    ha    = math.acos(-math.tan(lat_r) * math.tan(decl))
    return 12 - math.degrees(ha) / 15, 12 + math.degrees(ha) / 15


def _bg() -> Tuple[int, int, int]:
    return _CHARCOAL if _is_night() else _CREAM


def _caption_col() -> Tuple[int, int, int]:
    return _CAPTION_LIGHT if _is_night() else _CAPTION_WARM


def _border_col() -> Tuple[int, int, int]:
    return _BORDER_NIGHT if _is_night() else _BORDER_DAY


# ---------------------------------------------------------------------------
# Paper texture
# ---------------------------------------------------------------------------

def _make_canvas(width: int, height: int) -> Image.Image:
    """Return a background canvas, optionally with subtle paper grain."""
    bg = _bg()
    if config.PAPER_TEXTURE:
        try:
            import numpy as np  # type: ignore
            # ±6 per channel — about 2-3 % variation
            noise = np.random.randint(-6, 7, (height, width, 3), dtype=np.int16)
            base  = np.array(bg, dtype=np.int16)
            arr   = np.clip(base + noise, 0, 255).astype(np.uint8)
            return Image.fromarray(arr, "RGB")
        except ImportError:
            pass
    return Image.new("RGB", (width, height), bg)


# ---------------------------------------------------------------------------
# Font cache
# ---------------------------------------------------------------------------

_font_cache: dict = {}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key not in _font_cache:
        path = config.FONT_BOLD if bold else config.FONT
        try:
            _font_cache[key] = ImageFont.truetype(path, size)
        except Exception:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


# ---------------------------------------------------------------------------
# Overlay drawing helpers
# ---------------------------------------------------------------------------

def _draw_caption(
    draw:   ImageDraw.ImageDraw,
    text:   str,
    width:  int,
    height: int,
    colour: Tuple[int, int, int],
    align:  str = "left",
) -> None:
    if not text:
        return
    f   = _font(config.FONT_SIZE_CAPTION)
    box = draw.textbbox((0, 0), text, font=f)
    tw  = box[2] - box[0]
    th  = box[3] - box[1]
    y   = height - config.CAPTION_HEIGHT + (config.CAPTION_HEIGHT - th) // 2
    if align == "center":
        x = (width - tw) // 2
    elif align == "right":
        x = width - config.MARGIN - tw
    else:
        x = config.MARGIN
    draw.text((x, y), text, fill=colour, font=f)


def _draw_weather(
    draw:    ImageDraw.ImageDraw,
    weather: str,
    width:   int,
    height:  int,
    colour:  Tuple[int, int, int],
) -> None:
    if not weather:
        return
    f   = _font(config.FONT_SIZE_SMALL)
    box = draw.textbbox((0, 0), weather, font=f)
    tw  = box[2] - box[0]
    th  = box[3] - box[1]
    x   = width  - config.MARGIN - tw
    y   = height - config.CAPTION_HEIGHT + (config.CAPTION_HEIGHT - th) // 2
    draw.text((x, y), weather, fill=colour, font=f)


def _draw_clock(
    draw:   ImageDraw.ImageDraw,
    width:  int,
    height: int,
    colour: Tuple[int, int, int],
) -> None:
    text = datetime.now().strftime("%H:%M")
    f    = _font(config.FONT_SIZE_SMALL)
    box  = draw.textbbox((0, 0), text, font=f)
    tw   = box[2] - box[0]
    x    = width - config.MARGIN - tw
    y    = config.MARGIN
    draw.text((x, y), text, fill=colour, font=f)


def _add_overlays(
    draw:    ImageDraw.ImageDraw,
    caption: str,
    weather: Optional[str],
    width:   int,
    height:  int,
    colour:  Tuple[int, int, int],
) -> None:
    """Draw caption, optional weather badge, and optional clock."""
    _draw_caption(draw, caption, width, height, colour, align="left")
    if weather:
        _draw_weather(draw, weather, width, height, colour)
    if config.SHOW_CLOCK:
        _draw_clock(draw, width, height, colour)


# ---------------------------------------------------------------------------
# Overlay presence helper
# ---------------------------------------------------------------------------

def _caption_reserve(caption: str, weather: Optional[str]) -> int:
    """
    Return the height to reserve for the caption bar.
    If there is nothing to display at the bottom, return 0 so the image
    can expand to fill the full screen.
    Clock is positioned at the top and does not need bottom space.
    """
    if caption or weather:
        return config.CAPTION_HEIGHT
    return 0


# ---------------------------------------------------------------------------
# Individual layouts
# ---------------------------------------------------------------------------

def landscape_layout(
    img:        Image.Image,
    width:      int,
    height:     int,
    caption:    str,
    weather:    Optional[str],
    face_rects: List,
) -> Image.Image:
    """
    Near-full-screen landscape.

    When STYLE is "auto" the image is face-aware cropped to fill the screen.
    When STYLE is "gallery" it is fitted inside the mount with no cropping.
    """
    col        = _caption_col()
    canvas     = _make_canvas(width, height)
    cap_h      = _caption_reserve(caption, weather)

    usable_w = width  - config.MARGIN
    usable_h = height - cap_h - config.MARGIN

    if config.STYLE == "auto":
        from face_detect import face_aware_crop
        photo = face_aware_crop(img, usable_w, usable_h, face_rects)
    else:
        photo = img.copy()
        photo.thumbnail((usable_w, usable_h), Image.Resampling.LANCZOS)

    x = (width  - photo.width)  // 2
    y = (height - cap_h - photo.height) // 2
    canvas.paste(photo, (x, y))

    draw = ImageDraw.Draw(canvas)
    _add_overlays(draw, caption, weather, width, height, col)
    return canvas


def portrait_layout(
    img:        Image.Image,
    width:      int,
    height:     int,
    caption:    str,
    weather:    Optional[str],
    face_rects: List,
) -> Image.Image:
    """
    Portrait photo on a blurred copy of itself (BLUR_PORTRAITS=True),
    or a plain gallery mount (BLUR_PORTRAITS=False).
    """
    col   = _caption_col()
    cap_h = _caption_reserve(caption, weather)

    if config.BLUR_PORTRAITS:
        # Background: scale to fill, blur heavily, then darken/lighten
        bg = ImageOps.fit(img, (width, height), Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=22))
        brightness = 0.35 if _is_night() else 0.55
        bg     = ImageEnhance.Brightness(bg).enhance(brightness)
        canvas = bg.convert("RGB")
    else:
        canvas = _make_canvas(width, height)

    # Foreground: fit without cropping
    photo = img.copy()
    photo.thumbnail(
        (
            width  - config.MARGIN * 2,
            height - cap_h - config.MARGIN * 2,
        ),
        Image.Resampling.LANCZOS,
    )
    x = (width  - photo.width)  // 2
    y = (height - cap_h - photo.height) // 2
    canvas.paste(photo, (x, y))

    draw = ImageDraw.Draw(canvas)
    _add_overlays(draw, caption, weather, width, height, col)
    return canvas


def panorama_layout(
    img:     Image.Image,
    width:   int,
    height:  int,
    caption: str,
    weather: Optional[str],
) -> Image.Image:
    """
    Wide panorama letterboxed elegantly.

    The image is scaled to fill the full width; the background colour fills
    the bars above and below.
    """
    col    = _caption_col()
    canvas = _make_canvas(width, height)
    cap_h  = _caption_reserve(caption, weather)

    # Scale to fill width exactly (no horizontal cropping)
    scale   = width / img.width
    new_h   = int(img.height * scale)
    photo   = img.resize((width, new_h), Image.Resampling.LANCZOS)

    # Centre vertically in the space above the caption bar
    available_h = height - cap_h
    y = max(0, (available_h - new_h) // 2)
    canvas.paste(photo, (0, y))

    draw = ImageDraw.Draw(canvas)
    _add_overlays(draw, caption, weather, width, height, col)
    return canvas


def gallery_layout(
    img:     Image.Image,
    width:   int,
    height:  int,
    caption: str,
    weather: Optional[str],
) -> Image.Image:
    """Classic gallery mount: background surround and a fine border."""
    col   = _caption_col()
    cap_h = _caption_reserve(caption, weather)
    canvas = _make_canvas(width, height)

    photo = img.copy()
    photo.thumbnail(
        (
            width  - config.MARGIN * 2,
            height - cap_h - config.MARGIN * 2,
        ),
        Image.Resampling.LANCZOS,
    )
    x = (width  - photo.width)  // 2
    y = (height - cap_h - photo.height) // 2
    canvas.paste(photo, (x, y))

    draw = ImageDraw.Draw(canvas)
    draw.rectangle(
        (x - 2, y - 2, x + photo.width + 2, y + photo.height + 2),
        outline=_border_col(),
        width=1,
    )
    _add_overlays(draw, caption, weather, width, height, col)
    return canvas


def artwork_layout(
    img:     Image.Image,
    width:   int,
    height:  int,
    caption: str,
) -> Image.Image:
    """Art mode: gallery mount, no weather overlay."""
    return gallery_layout(img, width, height, caption, None)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def render(
    img:     Image.Image,
    meta:    dict,
    caption: str,
    weather: Optional[str],
    width:   int,
    height:  int,
) -> Image.Image:
    """
    Choose the best layout for this image and return the final PIL Image.
    """
    orientation  = meta.get("orientation", "landscape")
    face_rects   = meta.get("face_rects", [])

    if orientation == "panorama":
        return panorama_layout(img, width, height, caption, weather)

    if orientation == "portrait":
        return portrait_layout(img, width, height, caption, weather, face_rects)

    if orientation == "landscape" and config.STYLE == "auto":
        return landscape_layout(img, width, height, caption, weather, face_rects)

    # square, or landscape with STYLE="gallery"
    return gallery_layout(img, width, height, caption, weather)
