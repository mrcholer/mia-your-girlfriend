"""Portrait assets: the compact girl portrait and the legacy ANSI art."""

from __future__ import annotations

import re
from pathlib import Path

from .render import Span, display_width
from .theme import EMPTY, Style, Theme


_ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")
_FALLBACK = (
    "        .-\"\"\"\"-.",
    "      .'  .--.  '.",
    "     /   /    \\   \\",
    "    |   |  ()  |   |",
    "    |   |      |   |",
    "     \\   \\    /   /",
    "      '.  '--'  .'",
    "        '-....-'",
    "          MIA",
)


def asset_path(name: str) -> Path:
    return Path(__file__).resolve().parent.parent / name


def girl_lines() -> list[str]:
    """Return the user-provided braille portrait, preserving every cell."""

    path = asset_path("mia_girl.txt")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    return lines or list(_FALLBACK)


def girl_width() -> int:
    return max((display_width(line) for line in girl_lines()), default=0)


def legacy_ansi_lines(theme: Theme) -> list[list[Span]]:
    path = asset_path("mia_portrait.ans")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return parse_ansi(text, theme)


def parse_ansi(text: str, theme: Theme) -> list[list[Span]]:
    lines: list[list[Span]] = []
    for raw_line in text.splitlines():
        spans: list[Span] = []
        fg: tuple[int, int, int] | None = None
        bg: tuple[int, int, int] | None = None
        bold = False
        dim = False
        position = 0
        for match in _ANSI_RE.finditer(raw_line):
            chunk = raw_line[position : match.start()]
            if chunk:
                style = Style(fg=fg, bg=bg, bold=bold, dim=dim)
                if not theme.supports_color:
                    style = Style(bold=bold, dim=dim)
                if spans and spans[-1].style == style:
                    spans[-1] = Span(spans[-1].text + chunk, style)
                else:
                    spans.append(Span(chunk, style))
            parameters = [
                int(value) for value in match.group(1).split(";") if value != ""
            ]
            fg, bg, bold, dim = _apply_sgr(parameters, fg, bg, bold, dim)
            position = match.end()
        tail = raw_line[position:]
        if tail:
            style = Style(fg=fg, bg=bg, bold=bold, dim=dim)
            if not theme.supports_color:
                style = Style(bold=bold, dim=dim)
            spans.append(Span(tail, style))
        lines.append(spans)
    return lines


def _apply_sgr(
    parameters: list[int],
    fg: tuple[int, int, int] | None,
    bg: tuple[int, int, int] | None,
    bold: bool,
    dim: bool,
) -> tuple[
    tuple[int, int, int] | None,
    tuple[int, int, int] | None,
    bool,
    bool,
]:
    index = 0
    while index < len(parameters):
        code = parameters[index]
        if code == 0:
            fg = bg = None
            bold = dim = False
        elif code == 1:
            bold = True
        elif code == 2:
            dim = True
        elif code == 22:
            bold = dim = False
        elif code == 39:
            fg = None
        elif code == 49:
            bg = None
        elif code in (38, 48):
            color, consumed = _extended_color(parameters[index:])
            if color is not None:
                if code == 38:
                    fg = color
                else:
                    bg = color
                index += consumed - 1
        elif 30 <= code <= 37:
            fg = _basic_color(code - 30)
        elif 90 <= code <= 97:
            fg = _basic_color(code - 90 + 8)
        elif 40 <= code <= 47:
            bg = _basic_color(code - 40)
        elif 100 <= code <= 107:
            bg = _basic_color(code - 100 + 8)
        index += 1
    return fg, bg, bold, dim


def _extended_color(
    parameters: list[int],
) -> tuple[tuple[int, int, int] | None, int]:
    if len(parameters) < 2:
        return None, 1
    mode = parameters[1]
    if mode == 2 and len(parameters) >= 5:
        return (
            (parameters[2] % 256, parameters[3] % 256, parameters[4] % 256),
            5,
        )
    if mode == 5 and len(parameters) >= 3:
        return _ansi256_rgb(parameters[2] % 256), 3
    return None, 1


def _basic_color(index: int) -> tuple[int, int, int]:
    table = (
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
    return table[index % len(table)]


def _ansi256_rgb(index: int) -> tuple[int, int, int]:
    if index < 16:
        return _basic_color(index)
    if index >= 232:
        value = 8 + (index - 232) * 10
        return value, value, value
    index -= 16
    levels = (0, 95, 135, 175, 215, 255)
    return (
        levels[index // 36],
        levels[(index // 6) % 6],
        levels[index % 6],
    )
