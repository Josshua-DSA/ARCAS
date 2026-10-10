"""Theme configuration for Terminal User Interface (Rich & Textual)."""

from rich.theme import Theme

# Palette Tokens
COLOR_ACCENT = "#FF7517"     # Primary orange accent
COLOR_SURFACE = "#3E3939"    # Card / Panel surface
COLOR_BASE = "#2C2727"       # Canvas background
COLOR_FOREGROUND = "#F6F4F4" # Off-white primary text

COLOR_MUTED = "#8E8686"
COLOR_BULLISH = "#52B788"
COLOR_BEARISH = "#E63946"

RICH_THEME = Theme({
    "accent": COLOR_ACCENT,
    "surface": COLOR_SURFACE,
    "base": COLOR_BASE,
    "foreground": COLOR_FOREGROUND,
    "muted": COLOR_MUTED,
    "bullish": COLOR_BULLISH,
    "bearish": COLOR_BEARISH,
    "info": COLOR_ACCENT,
    "warning": "#FFB703",
    "danger": COLOR_BEARISH,
    "success": COLOR_BULLISH,
})
