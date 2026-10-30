"""Color capabilities, palette, and immutable terminal styles."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from enum import Enum
from functools import lru_cache


RGB = tuple[int, int, int]


class ColorDepth(str, Enum):
    NONE = "none"
    BASIC = "basic"
    ANSI256 = "ansi256"
    TRUECOLOR = "truecolor"


@dataclass(frozen=True)
class Style:
    fg: RGB | None = None
    bg: RGB | None = None
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    reverse: bool = False

    def with_(self, **changes: object) -> "Style":
        return replace(self, **changes)


EMPTY = Style()


# The 16 standard xterm colors, used for the basic-color fallback.
_BASIC_RGB: tuple[RGB, ...] = (
    (0, 0, 0),
    (128, 0, 0),
    (0, 128, 0),
    (128, 128, 0),
    (0, 0, 128),
    (128, 0, 128),
    (0, 128, 128),
    (192, 192, 192),
    (128, 128, 128),
    (255, 0, 0),
    (0, 255, 0),
    (255, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
)


def detect_color_depth(enabled: bool) -> ColorDepth:
    if not enabled:
        return ColorDepth.NONE
    colorterm = os.environ.get("COLORTERM", "").lower()
    term = os.environ.get("TERM", "").lower()
    if colorterm in {"truecolor", "24bit"} or "direct" in term:
        return ColorDepth.TRUECOLOR
    if os.name == "nt" and (os.environ.get("WT_SESSION") or term):
        return ColorDepth.TRUECOLOR
    if "256color" in term:
        return ColorDepth.ANSI256
    return ColorDepth.BASIC


def _nearest(rgb: RGB, palette: tuple[RGB, ...]) -> int:
    r, g, b = rgb
    best_index = 0
    best_distance = 1 << 60
    for index, (pr, pg, pb) in enumerate(palette):
        distance = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if distance < best_distance:
            best_distance = distance
            best_index = index
    return best_index


@lru_cache(maxsize=256)
def _rgb_to_ansi256(rgb: RGB) -> int:
    levels = (0, 95, 135, 175, 215, 255)
    best = 16
    best_distance = 1 << 60
    for r_index, r_value in enumerate(levels):
        for g_index, g_value in enumerate(levels):
            for b_index, b_value in enumerate(levels):
                distance = (
                    (rgb[0] - r_value) ** 2
                    + (rgb[1] - g_value) ** 2
                    + (rgb[2] - b_value) ** 2
                )
                if distance < best_distance:
                    best_distance = distance
                    best = 16 + 36 * r_index + 6 * g_index + b_index
    for index in range(24):
        value = 8 + index * 10
        distance = sum((channel - value) ** 2 for channel in rgb)
        if distance < best_distance:
            best_distance = distance
            best = 232 + index
    return best


class Theme:
    """A small, cohesive palette that degrades to 256/basic/no-color."""

    def __init__(self, enabled: bool = True) -> None:
        self.depth = detect_color_depth(enabled)
        self.enabled = enabled

        self.text = Style(fg=(230, 226, 235))
        self.bright = Style(fg=(247, 244, 249), bold=True)
        self.muted = Style(fg=(148, 140, 158))
        self.faint = Style(fg=(92, 85, 104))
        self.border = Style(fg=(64, 57, 73))
        self.rule = Style(fg=(70, 62, 80))

        self.rose = Style(fg=(244, 164, 196))
        self.rose_bright = Style(fg=(255, 121, 165), bold=True)
        self.rose_dim = Style(fg=(188, 125, 152))
        self.rose_soft = Style(fg=(214, 146, 174))
        self.green = Style(fg=(159, 227, 161))
        self.cyan = Style(fg=(126, 211, 216))
        self.yellow = Style(fg=(242, 207, 122))
        self.red = Style(fg=(255, 125, 136))
        self.red_bright = Style(fg=(255, 105, 122), bold=True)

        self.mia = Style(fg=(244, 164, 196), bold=True)
        self.user = Style(fg=(159, 227, 161), bold=True)
        self.system = Style(fg=(148, 140, 158))

        if enabled:
            self.selection = Style(
                fg=(255, 241, 248),
                bg=(62, 43, 57),
                bold=True,
            )
            self.cursor = Style(fg=(30, 24, 31), bg=(244, 164, 196))
        else:
            self.selection = Style(reverse=True, bold=True)
            self.cursor = Style(reverse=True)
        self.overlay = EMPTY

    @property
    def supports_color(self) -> bool:
        return self.depth is not ColorDepth.NONE

    def code(self, style: Style) -> str:
        """Return an absolute SGR sequence for a style."""

        return _style_code(self.depth, style)

    def role(self, role: str) -> Style:
        if role in {"mia", "assistant", "rose", "accent"}:
            return self.rose
        if role in {"you", "user"}:
            return self.user
        if role == "error":
            return self.red
        if role == "success":
            return self.green
        if role == "warning":
            return self.yellow
        return self.system

    def status(self, status: str) -> tuple[str, Style]:
        mapping = {
            "online": ("●", self.green),
            "typing": ("●", self.rose_bright),
            "waiting": ("●", self.yellow),
            "quiet": ("●", self.yellow),
            "angry": ("●", self.red),
            "blocked": ("×", self.red),
            "closed": ("×", self.red),
            "closing": ("●", self.red),
        }
        return mapping.get(status, ("●", self.muted))


@lru_cache(maxsize=512)
def _style_code(depth: ColorDepth, style: Style) -> str:
    parts: list[str] = []
    if style.reverse:
        parts.append("7")
    if style.bold:
        parts.append("1")
    if style.dim:
        parts.append("2")
    if style.italic:
        parts.append("3")
    if style.underline:
        parts.append("4")

    if depth is not ColorDepth.NONE:
        if style.fg is not None:
            parts.extend(_color_codes(style.fg, depth, background=False))
        if style.bg is not None:
            parts.extend(_color_codes(style.bg, depth, background=True))

    if not parts:
        return "\x1b[0m"
    return "\x1b[0m\x1b[" + ";".join(parts) + "m"


def _color_codes(rgb: RGB, depth: ColorDepth, background: bool) -> list[str]:
    if depth is ColorDepth.TRUECOLOR:
        prefix = "48" if background else "38"
        return [f"{prefix};2;{rgb[0]};{rgb[1]};{rgb[2]}"]
    if depth is ColorDepth.ANSI256:
        prefix = "48" if background else "38"
        return [f"{prefix};5;{_rgb_to_ansi256(rgb)}"]
    index = _nearest(rgb, _BASIC_RGB)
    if background:
        return [str((40 if index < 8 else 100) + index % 8)]
    return [str((30 if index < 8 else 90) + index % 8)]
