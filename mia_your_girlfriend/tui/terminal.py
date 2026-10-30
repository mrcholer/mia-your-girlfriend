"""Raw terminal ownership, resize signals, and key input."""

from __future__ import annotations

import atexit
import os
import select
import signal
import sys
import termios
import tty
from typing import Any

from .keys import Key, KeyDecoder


_ENTER = (
    "\x1b[?1049h"  # alternate screen
    "\x1b[?25l"  # hide hardware cursor
    "\x1b[?7l"  # no autowrap; the canvas positions every row
    "\x1b[?2004h"  # bracketed paste
    "\x1b[?1000h\x1b[?1006h"  # wheel/mouse reports
    "\x1b[2J\x1b[H"
)

_EXIT = (
    "\x1b[?1000l\x1b[?1006l"
    "\x1b[?2004l"
    "\x1b[?7h"
    "\x1b[0m"
    "\x1b[?25h"
    "\x1b[?1049l"
)


class Terminal:
    """Own the tty for the lifetime of the TUI and always restore it."""

    def __init__(self) -> None:
        self.input_fd = sys.stdin.fileno()
        self.output_fd = sys.stdout.fileno()
        self._saved_attrs: list[Any] | None = None
        self._saved_handlers: dict[int, Any] = {}
        self._entered = False
        self._restored = False
        self._decoder = KeyDecoder()
        self._queue: list[Key] = []
        self._eof = False
        self._resized = False
        self._terminate = False
        self._atexit_registered = False

    def __enter__(self) -> "Terminal":
        self.enter()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.restore()

    def enter(self) -> None:
        if self._entered:
            return
        self._saved_attrs = termios.tcgetattr(self.input_fd)
        tty.setraw(self.input_fd)
        self._install_signals()
        self._entered = True
        self._restored = False
        atexit.register(self._emergency_restore)
        self._atexit_registered = True
        self.write(_ENTER)

    def restore(self) -> None:
        if self._restored:
            return
        self._restored = True
        try:
            self.write(_EXIT)
        except OSError:
            pass
        if self._entered and self._saved_attrs is not None:
            try:
                termios.tcsetattr(
                    self.input_fd, termios.TCSAFLUSH, self._saved_attrs
                )
            except (OSError, ValueError):
                pass
        self._restore_signals()
        if self._atexit_registered:
            try:
                atexit.unregister(self._emergency_restore)
            except (AttributeError, ValueError):
                pass
            self._atexit_registered = False
        self._entered = False

    def _emergency_restore(self) -> None:
        self.restore()

    def _install_signals(self) -> None:
        for sig in (signal.SIGWINCH, signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            try:
                self._saved_handlers[sig] = signal.getsignal(sig)
                signal.signal(sig, self._handle_signal)
            except (ValueError, OSError):
                pass

    def _restore_signals(self) -> None:
        for sig, handler in self._saved_handlers.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass
        self._saved_handlers.clear()

    def _handle_signal(self, signum: int, frame: object) -> None:
        if signum == signal.SIGWINCH:
            self._resized = True
        else:
            self._terminate = True

    def write(self, text: str) -> None:
        if not text:
            return
        try:
            os.write(self.output_fd, text.encode("utf-8", "replace"))
        except OSError:
            self._eof = True

    def size(self) -> tuple[int, int]:
        try:
            size = os.get_terminal_size(self.output_fd)
            return max(1, size.columns), max(1, size.lines)
        except OSError:
            try:
                size = os.get_terminal_size(self.input_fd)
                return max(1, size.columns), max(1, size.lines)
            except OSError:
                return 100, 30

    def take_resize(self) -> bool:
        resized = self._resized
        self._resized = False
        return resized

    def should_terminate(self) -> bool:
        return self._terminate

    def read_key(self, timeout: float | None) -> Key | None:
        if self._queue:
            return self._queue.pop(0)
        if self._eof:
            return Key("eof")

        ready = self._select(timeout)
        if not ready:
            if self._decoder.buffer == b"\x1b":
                self._queue.extend(self._decoder.flush_escape())
                if self._queue:
                    return self._queue.pop(0)
            return None

        try:
            data = os.read(self.input_fd, 4096)
        except OSError:
            self._eof = True
            return Key("eof")
        if not data:
            self._eof = True
            return Key("eof")

        keys = self._decoder.feed(data)
        if not keys and self._decoder.buffer == b"\x1b":
            # Escape arrives as one byte. Give a possible sequence a brief
            # chance to finish before treating it as Esc.
            if self._select(0.03):
                try:
                    more = os.read(self.input_fd, 64)
                except OSError:
                    more = b""
                if more:
                    keys.extend(self._decoder.feed(more))
            if not keys:
                keys.extend(self._decoder.flush_escape())
        if keys:
            self._queue.extend(keys)
            return self._queue.pop(0)
        return None

    def _select(self, timeout: float | None) -> bool:
        try:
            ready, _, _ = select.select([self.input_fd], [], [], timeout)
        except (OSError, ValueError):
            return False
        return bool(ready)
