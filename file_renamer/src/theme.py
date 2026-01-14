"""
Theme - Design System for File Renamer Pro
Creative Studio Dark Theme with cross-platform font support
"""

import sys


def get_platform_fonts():
    """Get appropriate fonts for the current platform"""
    if sys.platform == 'darwin':  # macOS
        return {
            'display': ('SF Pro Display', 'Helvetica Neue', 'Arial'),
            'body': ('SF Pro Text', 'Helvetica Neue', 'Arial'),
            'mono': ('SF Mono', 'Menlo', 'Monaco', 'Courier New'),
        }
    elif sys.platform == 'win32':  # Windows
        return {
            'display': ('Segoe UI', 'Arial'),
            'body': ('Segoe UI', 'Arial'),
            'mono': ('Cascadia Code', 'Consolas', 'Courier New'),
        }
    else:  # Linux and others
        return {
            'display': ('Ubuntu', 'DejaVu Sans', 'Arial'),
            'body': ('Ubuntu', 'DejaVu Sans', 'Arial'),
            'mono': ('Ubuntu Mono', 'DejaVu Sans Mono', 'Courier New'),
        }


class Theme:
    """Design tokens for the Creative Studio aesthetic"""

    # Get platform-appropriate fonts
    _fonts = get_platform_fonts()

    # Core palette
    BG_PRIMARY = "#1a1a1f"
    BG_SECONDARY = "#242429"
    BG_TERTIARY = "#2d2d33"
    BG_ELEVATED = "#35353d"

    # Accent colors
    ACCENT_PRIMARY = "#ff6b35"    # Coral - primary actions
    ACCENT_SECONDARY = "#4ecdc4"  # Teal - info
    ACCENT_SUCCESS = "#45b764"    # Green
    ACCENT_WARNING = "#ffc857"    # Amber
    ACCENT_DANGER = "#ff4757"     # Red
    ACCENT_PURPLE = "#a855f7"     # Purple - for production

    # Drop zone colors
    DROP_MAIN_DESIGN = "#2a4858"      # Blue-teal for main design
    DROP_VIRTUAL_PROOF = "#3d2a4d"    # Purple for proofs
    DROP_PRODUCTION = "#2d3a2d"       # Green for production

    # Text colors
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#a0a0a8"
    TEXT_TERTIARY = "#6b6b75"
    TEXT_ON_ACCENT = "#ffffff"

    # Borders
    BORDER_SUBTLE = "#3a3a42"
    BORDER_DEFAULT = "#4a4a55"
    BORDER_FOCUS = "#ff6b35"

    # Typography - using platform-appropriate fonts
    FONT_DISPLAY = (_fonts['display'][0], 10, "bold")
    FONT_BODY = (_fonts['body'][0], 9)
    FONT_SMALL = (_fonts['body'][0], 8)
    FONT_MONO = (_fonts['mono'][0], 9)
    FONT_MONO_LARGE = (_fonts['mono'][0], 28, "bold")
    FONT_BUTTON = (_fonts['body'][0], 9)
    FONT_TITLE = (_fonts['display'][0], 18, "bold")
    FONT_SECTION = (_fonts['body'][0], 9)

    # Spacing
    PAD_XS = 3
    PAD_SM = 6
    PAD_MD = 10
    PAD_LG = 12
    PAD_XL = 18

    # Animation/Timing
    HOVER_DELAY = 50  # ms
    TOOLTIP_DELAY = 500  # ms

    @classmethod
    def get_color_variants(cls, base_color: str) -> dict:
        """Generate hover and disabled variants of a color"""
        # Simple brightening for hover
        return {
            'normal': base_color,
            'hover': cls._adjust_brightness(base_color, 1.15),
            'disabled': cls.BG_TERTIARY,
        }

    @staticmethod
    def _adjust_brightness(hex_color: str, factor: float) -> str:
        """Adjust the brightness of a hex color"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        new_rgb = tuple(min(255, int(c * factor)) for c in rgb)
        return f"#{new_rgb[0]:02x}{new_rgb[1]:02x}{new_rgb[2]:02x}"
