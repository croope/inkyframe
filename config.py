from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PHOTO_DIR   = Path("/home/chris/Strawsons")
ARTWORK_DIR = Path("/home/chris/Artwork")
STATE_FILE  = Path("/home/chris/.photoframe_state.json")
DB_FILE     = Path("/home/chris/.photoframe.db")

# ---------------------------------------------------------------------------
# Display style
#   "auto"    — intelligently chosen per image (recommended)
#   "gallery" — always use a white/cream mount regardless of orientation
# ---------------------------------------------------------------------------

STYLE = "auto"

# ---------------------------------------------------------------------------
# Overlays
# ---------------------------------------------------------------------------

SHOW_WEATHER   = False   # Requires WEATHER_API_KEY and WEATHER_LOCATION below
SHOW_CLOCK     = False   # Tiny clock in top-right corner
SHOW_DATE      = True    # EXIF date in caption
SHOW_LOCATION  = True    # GPS-derived place name in caption (needs internet or
                         # the optional reverse_geocoder package)
SHOW_FILENAME  = False   # Show filename stem as fallback caption

# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

BLUR_PORTRAITS  = True   # Blurred version of the photo as background for
                         # portrait images — makes them fill the screen nicely
FACE_DETECTION  = True   # Shift crop centre to keep faces in frame
                         # (requires opencv-python)
PAPER_TEXTURE   = True   # Subtle paper grain on background
                         # (requires numpy — falls back gracefully without it)

# ---------------------------------------------------------------------------
# Day / night theme
#   "auto"  — cream background during the day, charcoal after sunset
#   "day"   — always cream
#   "night" — always charcoal
# ---------------------------------------------------------------------------

DAY_NIGHT = "auto"

# Coordinates used for sunrise/sunset calculation (change to your location)
LATITUDE  = 52.1894
LONGITUDE = 1.1608

# ---------------------------------------------------------------------------
# Weather  (OpenWeatherMap free tier — https://openweathermap.org/api)
# ---------------------------------------------------------------------------

WEATHER_API_KEY  = ""           # Your API key
WEATHER_LOCATION = "Ipswich,GB"  # City name accepted by OWM
WEATHER_UNITS    = "metric"     # "metric" (°C) or "imperial" (°F)

# ---------------------------------------------------------------------------
# Fonts  (DejaVu is pre-installed on Raspberry Pi OS)
# ---------------------------------------------------------------------------

FONT      = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

FONT_SIZE_CAPTION = 22
FONT_SIZE_SMALL   = 16

# ---------------------------------------------------------------------------
# Layout geometry
# ---------------------------------------------------------------------------

MARGIN         = 36
CAPTION_HEIGHT = 48

# ---------------------------------------------------------------------------
# Supported image extensions
# ---------------------------------------------------------------------------

SUPPORTED = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".heic", ".HEIC"}

# ---------------------------------------------------------------------------
# Playlist
# ---------------------------------------------------------------------------

# How many recently shown images to remember (to avoid close repeats)
RECENT_WINDOW = 10
