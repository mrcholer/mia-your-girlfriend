"""Decode terminal input into small, named key events."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MouseEvent:
    button: int
    x: int
    y: int
    pressed: bool

    @property
    def wheel_up(self) -> bool:
        return self.button == 64

    @property
    def wheel_down(self) -> bool:
        return self.button == 65


@dataclass(frozen=True)
class Key:
    name: str
    text: str = ""
    mouse: MouseEvent | None = None


_CONTROL_NAMES = {
    0x01: "ctrl_a",
    0x02: "ctrl_b",
    0x03: "ctrl_c",
    0x04: "ctrl_d",
    0x05: "ctrl_e",
    0x06: "ctrl_f",
    0x07: "ctrl_g",
    0x08: "backspace",
    0x09: "tab",
    0x0A: "enter",
    0x0B: "ctrl_k",
    0x0C: "ctrl_l",
    0x0D: "enter",
    0x0E: "ctrl_n",
    0x0F: "ctrl_o",
    0x10: "ctrl_p",
    0x11: "ctrl_q",
    0x12: "ctrl_r",
    0x13: "ctrl_s",
    0x14: "ctrl_t",
    0x15: "ctrl_u",
    0x16: "ctrl_v",
    0x17: "ctrl_w",
    0x18: "ctrl_x",
    0x19: "ctrl_y",
    0x1A: "ctrl_z",
    0x1C: "ctrl_backslash",
    0x1D: "ctrl_bracket",
    0x1E: "ctrl_caret",
    0x1F: "ctrl_underscore",
    0x7F: "backspace",
}


_SEQUENCES = {
    b"\x1b[A": "up",
    b"\x1b[B": "down",
    b"\x1b[C": "right",
    b"\x1b[D": "left",
    b"\x1bOA": "up",
    b"\x1bOB": "down",
    b"\x1bOC": "right",
    b"\x1bOD": "left",
    b"\x1b[H": "home",
    b"\x1b[F": "end",
    b"\x1bOH": "home",
    b"\x1bOF": "end",
    b"\x1b[1~": "home",
    b"\x1b[2~": "insert",
    b"\x1b[3~": "delete",
    b"\x1b[4~": "end",
    b"\x1b[5~": "pageup",
    b"\x1b[6~": "pagedown",
    b"\x1b[7~": "home",
    b"\x1b[8~": "end",
    b"\x1b[Z": "backtab",
    b"\x1bOP": "f1",
    b"\x1bOQ": "f2",
    b"\x1bOR": "f3",
    b"\x1bOS": "f4",
    b"\x1b[11~": "f1",
    b"\x1b[12~": "f2",
    b"\x1b[13~": "f3",
    b"\x1b[14~": "f4",
    b"\x1b[15~": "f5",
    b"\x1b[17~": "f6",
    b"\x1b[18~": "f7",
    b"\x1b[19~": "f8",
    b"\x1b[20~": "f9",
    b"\x1b[21~": "f10",
    b"\x1b[23~": "f11",
    b"\x1b[24~": "f12",
    b"\x1b[1;2A": "shift_up",
    b"\x1b[1;2B": "shift_down",
    b"\x1b[1;5A": "ctrl_up",
    b"\x1b[1;5B": "ctrl_down",
    b"\x1b[1;5C": "ctrl_right",
    b"\x1b[1;5D": "ctrl_left",
}

_MOUSE_RE = re.compile(rb"^\x1b\[<(\d+);(\d+);(\d+)([Mm])")
_MODIFIER_RE = re.compile(rb"^\x1b\[1;(\d+)([A-Za-z~])")


class KeyDecoder:
    """Incremental decoder for UTF-8, CSI, SS3, paste, and SGR mouse input."""

    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[Key]:
        self.buffer.extend(data)
        keys: list[Key] = []
        while self.buffer:
            key, consumed = self._next()
            if consumed == 0:
                break
            del self.buffer[:consumed]
            if key is not None:
                keys.append(key)
        return keys

    def flush_escape(self) -> list[Key]:
        if self.buffer == b"\x1b":
            self.buffer.clear()
            return [Key("esc")]
        return []

    def has_pending(self) -> bool:
        return bool(self.buffer)

    def clear(self) -> None:
        self.buffer.clear()

    def _next(self) -> tuple[Key | None, int]:
        data = bytes(self.buffer)
        if not data:
            return None, 0

        if data[0] == 0x1B:
            return self._escape(data)

        byte = data[0]
        if byte in _CONTROL_NAMES:
            return Key(_CONTROL_NAMES[byte]), 1

        if byte < 0x80:
            char = chr(byte)
            return Key("char", char), 1

        expected = _utf8_length(byte)
        if expected == 0:
            return None, 1
        if len(data) < expected:
            return None, 0
        chunk = data[:expected]
        try:
            char = chunk.decode("utf-8")
        except UnicodeDecodeError:
            return None, 1
        if char == " ":
            return Key("space", " "), expected
        return Key("char", char), expected

    def _escape(self, data: bytes) -> tuple[Key | None, int]:
        if len(data) == 1:
            return None, 0

        if data.startswith(b"\x1b[200~"):
            end = data.find(b"\x1b[201~", 6)
            if end < 0:
                return None, 0
            text = data[6:end].decode("utf-8", "replace")
            return Key("paste", text), end + 6

        mouse_match = _MOUSE_RE.match(data)
        if mouse_match:
            button = int(mouse_match.group(1))
            x = int(mouse_match.group(2))
            y = int(mouse_match.group(3))
            pressed = mouse_match.group(4) == b"M"
            return (
                Key("mouse", mouse=MouseEvent(button, x - 1, y - 1, pressed)),
                mouse_match.end(),
            )

        for sequence, name in _SEQUENCES.items():
            if data.startswith(sequence):
                return Key(name), len(sequence)

        if data.startswith(b"\x1b[") or data.startswith(b"\x1bO"):
            end = _csi_end(data)
            if end is None:
                return None, 0
            sequence = data[:end]
            modifier = _MODIFIER_RE.match(sequence)
            if modifier:
                code = modifier.group(1)
                final = modifier.group(2)
                direction = {
                    b"A": "up",
                    b"B": "down",
                    b"C": "right",
                    b"D": "left",
                    b"H": "home",
                    b"F": "end",
                }.get(final)
                if direction:
                    prefix = {2: "shift_", 3: "alt_", 5: "ctrl_"}.get(
                        int(code), ""
                    )
                    return Key(prefix + direction), end
            return Key("unknown", sequence.decode("ascii", "replace")), end

        if len(data) >= 2 and 0x20 <= data[1] < 0x7F:
            return Key("alt", chr(data[1])), 2

        return Key("esc"), 1


def _utf8_length(byte: int) -> int:
    if 0xC2 <= byte <= 0xDF:
        return 2
    if 0xE0 <= byte <= 0xEF:
        return 3
    if 0xF0 <= byte <= 0xF4:
        return 4
    return 0


def _csi_end(data: bytes) -> int | None:
    for index in range(2, len(data)):
        byte = data[index]
        if 0x40 <= byte <= 0x7E:
            return index + 1
    return None
