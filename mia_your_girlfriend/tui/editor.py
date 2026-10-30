"""A small single-line editor with history and horizontal scrolling."""

from __future__ import annotations

from dataclasses import dataclass, field

from .render import char_width, display_width


MAX_INPUT = 500


@dataclass
class LineEditor:
    text: str = ""
    cursor: int = 0
    history: list[str] = field(default_factory=list)
    _history_index: int | None = None
    _history_draft: str = ""

    @property
    def has_text(self) -> bool:
        return bool(self.text.strip())

    def clear(self) -> None:
        self.text = ""
        self.cursor = 0
        self._history_index = None

    def set_text(self, text: str) -> None:
        self.text = text[:MAX_INPUT]
        self.cursor = len(self.text)
        self._history_index = None

    def insert(self, text: str) -> None:
        if not text:
            return
        text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
        room = MAX_INPUT - len(self.text)
        if room <= 0:
            return
        text = text[:room]
        self.text = self.text[: self.cursor] + text + self.text[self.cursor :]
        self.cursor += len(text)
        self._history_index = None

    def backspace(self) -> None:
        if self.cursor <= 0:
            return
        self.text = self.text[: self.cursor - 1] + self.text[self.cursor :]
        self.cursor -= 1

    def delete(self) -> None:
        if self.cursor >= len(self.text):
            return
        self.text = self.text[: self.cursor] + self.text[self.cursor + 1 :]

    def left(self) -> None:
        self.cursor = max(0, self.cursor - 1)

    def right(self) -> None:
        self.cursor = min(len(self.text), self.cursor + 1)

    def home(self) -> None:
        self.cursor = 0

    def end(self) -> None:
        self.cursor = len(self.text)

    def word_left(self) -> None:
        index = self.cursor
        while index > 0 and self.text[index - 1].isspace():
            index -= 1
        while index > 0 and not self.text[index - 1].isspace():
            index -= 1
        self.cursor = index

    def word_right(self) -> None:
        index = self.cursor
        length = len(self.text)
        while index < length and not self.text[index].isspace():
            index += 1
        while index < length and self.text[index].isspace():
            index += 1
        self.cursor = index

    def kill_to_start(self) -> None:
        self.text = self.text[self.cursor :]
        self.cursor = 0

    def kill_to_end(self) -> None:
        self.text = self.text[: self.cursor]

    def delete_word_before(self) -> None:
        original = self.cursor
        self.word_left()
        start = self.cursor
        self.text = self.text[:start] + self.text[original:]
        self.cursor = start

    def delete_word_after(self) -> None:
        start = self.cursor
        self.word_right()
        self.text = self.text[:start] + self.text[self.cursor :]
        self.cursor = start

    def history_prev(self) -> None:
        if not self.history:
            return
        if self._history_index is None:
            self._history_draft = self.text
            self._history_index = len(self.history)
        if self._history_index > 0:
            self._history_index -= 1
            self.text = self.history[self._history_index]
            self.cursor = len(self.text)
        elif self._history_index == 0:
            self.text = self.history[0]
            self.cursor = len(self.text)

    def history_next(self) -> None:
        if self._history_index is None:
            return
        if self._history_index < len(self.history) - 1:
            self._history_index += 1
            self.text = self.history[self._history_index]
        else:
            self._history_index = None
            self.text = self._history_draft
        self.cursor = len(self.text)

    def submit(self) -> str:
        value = self.text.strip()
        if value and (not self.history or self.history[-1] != value):
            self.history.append(value)
            if len(self.history) > 100:
                del self.history[0]
        self.clear()
        return value

    def window(self, width: int) -> tuple[str, int, bool, int]:
        """Return (visible text, cursor column, clipped-left, start index)."""

        if width <= 0:
            return "", 0, True, 0

        widths = [char_width(char) for char in self.text]
        cursor_column = sum(widths[: self.cursor])
        start = 0
        start_column = 0
        while start < self.cursor and cursor_column - start_column >= width:
            start_column += widths[start]
            start += 1

        end = start
        used = 0
        while end < len(self.text) and used + widths[end] <= width:
            used += widths[end]
            end += 1
        return self.text[start:end], cursor_column - start_column, start > 0, start

    def cursor_column(self) -> int:
        return display_width(self.text[: self.cursor])
