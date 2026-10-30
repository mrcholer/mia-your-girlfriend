"""Width-aware text layout and a small double-buffered ANSI canvas."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .theme import EMPTY, RGB, Style, Theme


_ZERO_WIDTH = {"\u200b", "\u200c", "\u200d", "\ufe0e", "\ufe0f"}


def char_width(char: str) -> int:
    if not char:
        return 0
    if char in _ZERO_WIDTH or unicodedata.combining(char):
        return 0
    if ord(char) < 32 or 0x7F <= ord(char) < 0xA0:
        return 0
    if unicodedata.east_asian_width(char) in {"W", "F"}:
        return 2
    return 1


def display_width(text: str) -> int:
    return sum(char_width(char) for char in text)


def split_at_width(text: str, width: int) -> tuple[str, str]:
    """Split text after at most *width* display columns."""

    if width <= 0:
        return "", text
    used = 0
    index = 0
    for index, char in enumerate(text):
        size = char_width(char)
        if size and used + size > width:
            return text[:index], text[index:]
        used += size
    return text, ""


def truncate(text: str, width: int, ellipsis: str = "…") -> str:
    if width <= 0:
        return ""
    if display_width(text) <= width:
        return text
    ellipsis_width = display_width(ellipsis)
    if width <= ellipsis_width:
        return split_at_width(text, width)[0]
    head, _ = split_at_width(text, width - ellipsis_width)
    return head + ellipsis


def pad(text: str, width: int, align: str = "left") -> str:
    text = truncate(text, width)
    remaining = max(0, width - display_width(text))
    if align == "right":
        return " " * remaining + text
    if align == "center":
        left = remaining // 2
        return " " * left + text + " " * (remaining - left)
    return text + " " * remaining


def wrap_text(text: str, width: int) -> list[str]:
    """Wrap prose by display width, preserving explicit line breaks."""

    if width <= 0:
        return [""]
    output: list[str] = []
    for hard_line in text.split("\n"):
        if hard_line == "":
            output.append("")
            continue
        words = hard_line.split(" ")
        line = ""
        for word in words:
            while display_width(word) > width:
                if line:
                    output.append(line)
                    line = ""
                head, word = split_at_width(word, width)
                output.append(head)
            if not word:
                continue
            if not line:
                line = word
                continue
            candidate = line + " " + word
            if display_width(candidate) <= width:
                line = candidate
            else:
                output.append(line)
                line = word
        if line or not output or (output and output[-1] != ""):
            output.append(line)
    return output or [""]


@dataclass(frozen=True)
class Span:
    text: str
    style: Style = EMPTY


def spans_width(spans: list[Span] | tuple[Span, ...]) -> int:
    return sum(display_width(span.text) for span in spans)


class Canvas:
    """A fixed-size cell canvas that only emits rows that changed."""

    def __init__(self, width: int, height: int, theme: Theme) -> None:
        self.width = max(1, width)
        self.height = max(1, height)
        self.theme = theme
        self.cells: list[list[tuple[str, Style]]] = []
        self._previous: list[str] = []
        self._full_clear = True
        self.clear()

    def resize(self, width: int, height: int) -> None:
        width = max(1, width)
        height = max(1, height)
        if (width, height) == (self.width, self.height):
            return
        self.width = width
        self.height = height
        self.invalidate()

    def invalidate(self) -> None:
        self._previous = []
        self._full_clear = True
        self.clear()

    def clear(self, style: Style = EMPTY) -> None:
        blank = (" ", style)
        self.cells = [[blank for _ in range(self.width)] for _ in range(self.height)]

    def _set(self, x: int, y: int, char: str, style: Style) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        row = self.cells[y]
        if row[x][0] == "":
            if x > 0:
                row[x - 1] = (" ", EMPTY)
        elif x + 1 < self.width and row[x + 1][0] == "":
            row[x + 1] = (" ", EMPTY)
        row[x] = (char, style)

    def put(
        self,
        x: int,
        y: int,
        text: str,
        style: Style = EMPTY,
        max_width: int | None = None,
    ) -> int:
        if not (0 <= y < self.height):
            return x
        limit = self.width if max_width is None else min(self.width, x + max_width)
        cursor = x
        for char in text:
            if char == "\t":
                char = " "
                size = 4
            else:
                size = char_width(char)
            if size == 0:
                if cursor > 0 and cursor - 1 < self.width:
                    previous, previous_style = self.cells[y][cursor - 1]
                    if previous not in {"", " "}:
                        self.cells[y][cursor - 1] = (previous + char, previous_style)
                continue
            if cursor + size > limit:
                break
            if cursor < 0:
                cursor += size
                continue
            self._set(cursor, y, char, style)
            if size == 2 and cursor + 1 < self.width:
                self._set(cursor + 1, y, "", style)
            cursor += size
        return cursor

    def put_right(self, right: int, y: int, text: str, style: Style = EMPTY) -> None:
        self.put(right - display_width(text), y, text, style)

    def put_center(self, x: int, y: int, width: int, text: str, style: Style = EMPTY) -> None:
        start = x + max(0, (width - display_width(text)) // 2)
        self.put(start, y, text, style)

    def fill(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        char: str = " ",
        style: Style = EMPTY,
    ) -> None:
        for row in range(max(0, y), min(self.height, y + height)):
            for column in range(max(0, x), min(self.width, x + width)):
                self._set(column, row, char, style)

    def hline(self, x: int, y: int, width: int, char: str = "─", style: Style = EMPTY) -> None:
        self.put(x, y, char * max(0, width), style)

    def vline(self, x: int, y: int, height: int, char: str = "│", style: Style = EMPTY) -> None:
        for row in range(max(0, y), min(self.height, y + height)):
            self._set(x, row, char, style)

    def box(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        style: Style = EMPTY,
        title: str | None = None,
        title_style: Style | None = None,
    ) -> None:
        if width < 2 or height < 2:
            return
        self.hline(x + 1, y, width - 2, "─", style)
        self.hline(x + 1, y + height - 1, width - 2, "─", style)
        self.vline(x, y + 1, height - 2, "│", style)
        self.vline(x + width - 1, y + 1, height - 2, "│", style)
        self.put(x, y, "╭", style)
        self.put(x + width - 1, y, "╮", style)
        self.put(x, y + height - 1, "╰", style)
        self.put(x + width - 1, y + height - 1, "╯", style)
        if title:
            self.put(
                x + 2,
                y,
                truncate(title, max(0, width - 4)),
                title_style or style,
            )

    def row_text(self, y: int) -> str:
        return "".join(char for char, _ in self.cells[y])

    def render(self) -> str:
        changed: list[tuple[int, str]] = []
        row_strings: list[str] = []
        for y, row in enumerate(self.cells):
            parts: list[str] = []
            current: Style | None = None
            for char, style in row:
                if char == "":
                    continue
                if style != current:
                    parts.append(self.theme.code(style))
                    current = style
                parts.append(char)
            if current not in {None, EMPTY}:
                parts.append("\x1b[0m")
            row_string = "".join(parts)
            row_strings.append(row_string)
            if y >= len(self._previous) or self._previous[y] != row_string:
                changed.append((y, row_string))

        self._previous = row_strings
        if not changed and not self._full_clear:
            return ""

        output = ["\x1b[?2026h"]
        if self._full_clear:
            output.append("\x1b[2J\x1b[H")
            self._full_clear = False
        for y, row_string in changed:
            output.append(f"\x1b[{y + 1};1H")
            output.append(row_string)
            output.append("\x1b[0m\x1b[K")
        output.append("\x1b[?2026l")
        return "".join(output)

    def force_full_redraw(self) -> None:
        self.invalidate()


def rgb_span(text: str, rgb: RGB) -> Span:
    return Span(text, Style(fg=rgb))
