"""The interactive chat application and its story playback loops."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .. import story
from ..state import StatePaths
from . import components
from .components import (
    BoxEntry,
    ChatEntry,
    RuleEntry,
    SceneEntry,
    SystemEntry,
    SPINNER,
)
from .editor import LineEditor
from .layout import compute_layout
from .render import Canvas
from .terminal import Terminal
from .theme import Theme


class ChatExit(Exception):
    """Unwind the active loop while preserving terminal cleanup."""


@dataclass
class Outcome:
    completed: bool = False
    quit_early: bool = False
    exit_code: int = 0


class MiaApp:
    def __init__(
        self,
        terminal: Terminal,
        theme: Theme,
        state_paths: StatePaths,
        fast: bool,
        first_run: bool,
    ) -> None:
        self.terminal = terminal
        self.theme = theme
        self.state = state_paths
        self.fast = fast
        self.first_run = first_run

        self.entries: list[components.Entry] = []
        self.editor = LineEditor()
        self.canvas: Canvas | None = None
        self.sidebar = True
        self.overlay: str | None = None
        self.help_scroll = 0
        self.portrait_scroll = 0
        self.portrait_legacy = False

        self.status = "online"
        self.status_label = "online"
        self.mood = "happy"
        self.episode = 1
        self.total_episodes = len(story.SCENES)
        self.affection = 0
        self.trust = 0
        self.replies = 0

        self.choice_mode = False
        self.choices: list[story.Choice] = []
        self.selected = 0
        self.wrapped_options: list[list[str]] = []
        self.streaming_index: int | None = None
        self.closing_progress: tuple[int, int] | None = None
        self.ending = False
        self.completed = False
        self.exit_code = 0

        self.scroll_top = 0
        self.pinned = True
        self.viewport_height = 1
        self.line_count = 0
        self.max_top = 0

        self.notice = ""
        self.notice_style = None
        self.notice_until = 0.0
        self.spinner_index = 0
        self._next_spinner = 0.0
        self.started_at = time.monotonic()

    # ------------------------------------------------------------------ run

    def run(self) -> Outcome:
        self.started_at = time.monotonic()
        try:
            if self.first_run:
                if self._splash():
                    return Outcome(quit_early=True)
                self.state.remember_welcome()
            self._play()
        except ChatExit:
            return Outcome(
                completed=self.completed,
                quit_early=not self.completed,
                exit_code=self.exit_code,
            )
        return Outcome(
            completed=self.completed,
            quit_early=not self.completed,
            exit_code=self.exit_code,
        )

    def _splash(self) -> bool:
        self.overlay = "splash"
        self.render()
        while True:
            key = self._poll(0.2)
            if key is None:
                continue
            if key.name in {"enter", "space"}:
                self.overlay = None
                self.render()
                return False
            if key.name in {"q", "esc", "ctrl_c"}:
                self.overlay = None
                self.render()
                return True
            if key.name == "p":
                self._portrait_overlay()
                self.overlay = "splash"
                self.render()
            elif key.name in {"?", "f1"}:
                self._help_overlay()
                self.overlay = "splash"
                self.render()

    def _play(self) -> None:
        self.episode = 1
        self.mood = "happy"
        self.set_status("online", "online")
        self.entries.append(
            SystemEntry("season 01 · a story in five chapters", icon="·")
        )
        self.entries.append(
            SystemEntry("MIA is online.", icon="●", tone="success")
        )
        self.render()
        self._stream_mia(story.INTRO)

        for scene in story.SCENES:
            self._enter_scene(scene)
            self._stream_mia(scene.question)
            choice = self._choose(scene)
            if scene.after:
                self._stream_mia(scene.after)

        self._finale()

    def _enter_scene(self, scene: story.Scene) -> None:
        self.episode = scene.episode
        self.mood = scene.mood
        self.set_status("online", "online")
        self.entries.append(SceneEntry(scene.episode, scene.title))
        self.pinned = True
        self.render()

    # --------------------------------------------------------------- story

    def _stream_mia(self, text: str) -> None:
        if self.fast:
            self.entries.append(ChatEntry("mia", text))
            self.set_status("online", "online")
            self.render()
            return

        index = len(self.entries)
        self.entries.append(ChatEntry("mia", ""))
        self.streaming_index = index
        self.set_status("typing", "typing")
        self.render()

        delay = 0.2 if self.streaming_index is not None else 0.0
        deadline = time.monotonic() + delay
        skipped = False
        while time.monotonic() < deadline:
            key = self._poll(0.04)
            if key is None:
                self.render()
                continue
            if self._global(key):
                continue
            if key.name == "enter":
                if self.editor.text.strip().startswith("/"):
                    value = self.editor.submit()
                    self._execute_command_or_notice(value)
                skipped = True
                break
            if key.name == "esc":
                skipped = True
                break
            self._feed_editor(key)
            skipped = True
            break

        if not skipped:
            revealed = 0
            length = len(text)
            while revealed < length:
                key = self._poll(0.022)
                if key is not None:
                    if self._global(key):
                        continue
                    if key.name in {"enter", "esc"}:
                        if key.name == "enter" and self.editor.text.strip().startswith("/"):
                            value = self.editor.submit()
                            self._execute_command_or_notice(value)
                        revealed = length
                        break
                    self._feed_editor(key)
                    revealed = length
                    break
                revealed = min(length, revealed + 2)
                self.entries[index] = ChatEntry("mia", text[:revealed])
                self.render()

        self.entries[index] = ChatEntry("mia", text)
        self.streaming_index = None
        self.set_status("online", "online")
        self.render()

    def _choose(self, scene: story.Scene) -> story.Choice:
        self.choices = list(scene.choices)
        self.choice_mode = True
        self.selected = 0
        self.set_status("waiting", "waiting")
        self.render()
        self.pinned = True

        while True:
            key = self._poll(0.15)
            if key is None:
                continue
            if self._global(key):
                continue
            if key.name == "ctrl_d" and not self.editor.has_text:
                raise ChatExit
            if key.name == "esc":
                if self.editor.has_text:
                    self.editor.clear()
                    self.render()
                continue
            if key.name == "tab":
                self.selected = (self.selected + 1) % len(self.choices)
                self.render()
                continue
            if key.name == "backtab":
                self.selected = (self.selected - 1) % len(self.choices)
                self.render()
                continue
            if key.name in {"up", "left"}:
                self.selected = (self.selected - 1) % len(self.choices)
                self.render()
                continue
            if key.name in {"down", "right"}:
                self.selected = (self.selected + 1) % len(self.choices)
                self.render()
                continue
            if key.name == "enter":
                value = self.editor.submit()
                if not value:
                    return self._choose_index(self.selected)
                if value.startswith("/"):
                    reply = self._parse_reply_command(value)
                    if reply is not None:
                        return self._choose_index(reply)
                    if self._execute_command_or_notice(value):
                        self.render()
                        continue
                    continue
                if value.isdigit() and 1 <= int(value) <= len(self.choices):
                    return self._choose_index(int(value) - 1)
                self.set_notice(
                    f"choose a reply from 1–{len(self.choices)}, or use ↑↓ and enter",
                    "warning",
                )
                self.render()
                continue
            if (
                key.name == "char"
                and key.text.isdigit()
                and not self.editor.has_text
            ):
                index = int(key.text) - 1
                if 0 <= index < len(self.choices):
                    self.selected = index
                    self.render()
                    continue
            self._feed_editor(key)
            self.render()

    def _choose_index(self, index: int) -> story.Choice:
        choice = self.choices[index]
        self.choice_mode = False
        self.choices = []
        self.selected = 0
        self.editor.clear()
        self.entries.append(ChatEntry("you", choice.text))
        self.affection += choice.affection
        self.trust += choice.trust
        self.replies += 1
        self.set_status("online", "online")
        self.pinned = True
        self.render()
        return choice

    def _parse_reply_command(self, value: str) -> int | None:
        parts = value.split()
        if len(parts) != 2 or parts[0] != "/reply" or not parts[1].isdigit():
            return None
        index = int(parts[1]) - 1
        if 0 <= index < len(self.choices):
            return index
        return None

    def _finale(self) -> None:
        self.episode = len(story.SCENES)
        self.mood = "angry"
        self.entries.append(SceneEntry(self.episode, "THE PLATFORM", finale=True))
        self.pinned = True
        self.render()

        self._stream_mia(story.finale_last_words(self.affection, self.trust))
        for message in story.FINALE_MESSAGES:
            self._stream_mia(message)

        self.entries.append(RuleEntry("link lost", "error"))
        self.entries.append(
            SystemEntry(story.FINALE_SIGNAL, tone="error", icon="×")
        )
        self.render()

        self.set_status("closing", "closing")
        errors = story.FINALE_ERRORS
        self.closing_progress = (0, len(errors))
        index = 0
        while index < len(errors):
            self.entries.append(
                SystemEntry(errors[index], tone="error", icon="×")
            )
            index += 1
            self.closing_progress = (index, len(errors))
            self.render()
            if self.fast:
                continue
            key = self._poll(0.075)
            if key is None:
                continue
            if self._global(key):
                continue
            for remaining in errors[index:]:
                self.entries.append(
                    SystemEntry(remaining, tone="error", icon="×")
                )
            index = len(errors)
            self.closing_progress = (index, len(errors))

        self.closing_progress = None
        self.entries.append(
            BoxEntry("signal lost", story.RELATIONSHIP_STATUS, tone="red")
        )
        self.entries.append(
            SystemEntry(
                story.statistics(self.replies, self.affection, self.trust),
                icon="·",
            )
        )
        saved, failures = self.state.close_season()
        if saved:
            self.entries.append(
                SystemEntry("season closed · chat archived", tone="error", icon="×")
            )
        else:
            message = failures[0] if failures else "unknown error"
            self.entries.append(
                SystemEntry(
                    f"ERR 034  unable to save permanent block: {message}",
                    tone="error",
                    icon="×",
                )
            )
            self.exit_code = 1

        self.completed = True
        self.ending = True
        self.set_status("closed", "closed")
        self.pinned = True
        self.render()
        self._hold_end()

    def _hold_end(self) -> None:
        while True:
            key = self._poll(0.2)
            if key is None:
                continue
            if key.name in {"enter", "esc", "q", "ctrl_c"}:
                return
            if self._global(key):
                continue

    # ------------------------------------------------------------- commands

    def _execute_command_or_notice(self, value: str) -> bool:
        if self._execute_command(value):
            return True
        name = value.split()[0] if value.split() else value
        self.set_notice(f"unknown command: {name} · /help lists commands", "warning")
        self.render()
        return False

    def _execute_command(self, value: str) -> bool:
        parts = value.split()
        if not parts:
            return False
        command = parts[0].lower()
        if command in {"/help", "/?", "/keys"}:
            self._help_overlay()
            return True
        if command == "/portrait":
            legacy = len(parts) > 1 and parts[1] == "legacy"
            self._portrait_overlay(legacy)
            return True
        if command == "/status":
            self.entries.append(
                SystemEntry(
                    (
                        f"chapter {self.episode:02d} / {self.total_episodes:02d}"
                        f"  ·  replies {self.replies:02d}"
                        f"  ·  mood {story.MOODS[self.mood][1].lower()}"
                        f"  ·  connection {self.status}"
                    ),
                    icon="·",
                )
            )
            self.pinned = True
            self.render()
            return True
        if command == "/clear":
            if self.streaming_index is not None:
                self.set_notice(
                    "wait for Mia to finish typing before clearing",
                    "warning",
                )
                self.render()
                return True
            self.entries.clear()
            self.entries.append(
                SystemEntry("chat view cleared.", tone="success", icon="✓")
            )
            self.scroll_top = 0
            self.pinned = True
            self.render()
            return True
        if command == "/about":
            self.entries.append(
                BoxEntry(
                    "about",
                    (
                        "mia-your-girlfriend 2.0",
                        "A terminal romance in five chapters.",
                        "Your replies shape how Mia remembers the season.",
                        "Built on the Python standard library.",
                    ),
                    tone="rose",
                )
            )
            self.pinned = True
            self.render()
            return True
        if command in {"/quit", "/exit"}:
            raise ChatExit
        return False

    # --------------------------------------------------------------- overlays

    def _help_overlay(self) -> None:
        self.overlay = "help"
        self.help_scroll = 0
        self.render()
        while True:
            key = self._poll(0.2)
            if key is None:
                continue
            if key.name == "ctrl_c":
                raise ChatExit
            if key.name in {"esc", "q", "?", "f1", "enter"}:
                break
            if key.name in {"up", "shift_up"}:
                self.help_scroll = max(0, self.help_scroll - 1)
                self.render()
            elif key.name in {"down", "shift_down"}:
                self.help_scroll = min(20, self.help_scroll + 1)
                self.render()
            elif key.name == "pageup":
                self.help_scroll = max(0, self.help_scroll - 6)
                self.render()
            elif key.name == "pagedown":
                self.help_scroll = min(20, self.help_scroll + 6)
                self.render()
            elif key.name == "mouse" and key.mouse:
                if key.mouse.wheel_up:
                    self.help_scroll = max(0, self.help_scroll - 2)
                    self.render()
                elif key.mouse.wheel_down:
                    self.help_scroll = min(20, self.help_scroll + 2)
                    self.render()
        self.overlay = None
        self.render()

    def _portrait_overlay(self, legacy: bool = False) -> None:
        self.overlay = "portrait_legacy" if legacy else "portrait"
        self.portrait_legacy = legacy
        self.portrait_scroll = 0
        self.render()
        while True:
            key = self._poll(0.2)
            if key is None:
                continue
            if key.name == "ctrl_c":
                raise ChatExit
            if key.name in {"esc", "q", "p", "enter"}:
                break
            if key.name in {"up", "shift_up"}:
                self.portrait_scroll = max(0, self.portrait_scroll - 1)
                self.render()
            elif key.name in {"down", "shift_down"}:
                self.portrait_scroll += 1
                self.render()
            elif key.name == "pageup":
                self.portrait_scroll = max(0, self.portrait_scroll - 8)
                self.render()
            elif key.name == "pagedown":
                self.portrait_scroll += 8
                self.render()
            elif key.name == "mouse" and key.mouse:
                if key.mouse.wheel_up:
                    self.portrait_scroll = max(0, self.portrait_scroll - 3)
                    self.render()
                elif key.mouse.wheel_down:
                    self.portrait_scroll += 3
                    self.render()
        self.overlay = None
        self.render()

    # ---------------------------------------------------------------- render

    def render(self) -> None:
        cols, rows = self.terminal.size()
        if self.canvas is None or (self.canvas.width, self.canvas.height) != (
            cols,
            rows,
        ):
            self.canvas = Canvas(cols, rows, self.theme)
        self.canvas.clear()
        if self.overlay == "splash":
            components.draw_splash(
                self.canvas, self.theme, first_run=self.first_run
            )
        elif self.overlay == "help":
            components.draw_help(self.canvas, self.theme, self.help_scroll)
        elif self.overlay in {"portrait", "portrait_legacy"}:
            components.draw_portrait(
                self.canvas,
                self.theme,
                self.portrait_scroll,
                legacy=self.overlay == "portrait_legacy",
            )
        else:
            self._render_main(cols, rows)
        output = self.canvas.render()
        self.terminal.write(output)

    def _render_main(self, cols: int, rows: int) -> None:
        base = compute_layout(cols, rows, self.sidebar, 0)
        self.wrapped_options = (
            components.wrap_options(self.choices, base.content_width)
            if self.choice_mode
            else []
        )
        count = (
            components.option_line_count(self.wrapped_options)
            if self.choice_mode
            else 0
        )
        layout = compute_layout(cols, rows, self.sidebar, count)
        if layout.too_small:
            components.draw_too_small(
                self.canvas, self.theme, suffix="q quit  ·  ctrl+c quit"
            )
            return

        spinner = SPINNER[self.spinner_index % len(SPINNER)]
        components.draw_header(
            self.canvas,
            layout,
            self.theme,
            self.status,
            self.status_label,
            self.episode,
            self.total_episodes,
            spinner,
        )
        if layout.sidebar:
            elapsed = int(time.monotonic() - self.started_at)
            elapsed_text = f"{elapsed // 60}:{elapsed % 60:02d}"
            components.draw_sidebar(
                self.canvas,
                layout,
                self.theme,
                self.status,
                self.status_label,
                story.MOODS[self.mood][1],
                self.episode,
                self.total_episodes,
                self.replies,
                elapsed_text,
            )

        lines = components.build_lines(
            self.entries,
            layout.content_width,
            self.theme,
            self.streaming_index,
            spinner,
        )
        height = layout.chat.height
        self.viewport_height = height
        self.line_count = len(lines)
        self.max_top = max(0, len(lines) - height)
        if self.pinned:
            self.scroll_top = self.max_top
        else:
            self.scroll_top = min(self.scroll_top, self.max_top)
            if self.scroll_top >= self.max_top:
                self.pinned = True

        top = self.scroll_top
        for offset, line in enumerate(lines[top : top + height]):
            components.draw_line(
                self.canvas,
                layout.chat.x,
                layout.chat.y + offset,
                line,
                layout.chat.width,
            )
        self._draw_scrollbar(layout)

        if self.choice_mode and layout.options:
            components.draw_options(
                self.canvas,
                layout,
                self.theme,
                self.choices,
                self.wrapped_options,
                self.selected,
            )

        components.draw_input(
            self.canvas,
            layout,
            self.theme,
            self.editor,
            enabled=not self.ending,
            placeholder=self._placeholder(),
        )
        left, style = self._footer_text()
        right = "↓ end" if not self.pinned and self.max_top > 0 else ""
        components.draw_footer(
            self.canvas, layout, self.theme, left, style, right
        )

    def _draw_scrollbar(self, layout) -> None:
        if (
            layout.scrollbar_x is None
            or self.max_top <= 0
            or layout.chat.height <= 1
        ):
            return
        height = layout.chat.height
        x = layout.scrollbar_x
        for offset in range(height):
            self.canvas.put(
                x, layout.chat.y + offset, "│", self.theme.faint
            )
        thumb_height = max(
            1, min(height, round(height * height / max(1, self.line_count)))
        )
        top = round((height - thumb_height) * self.scroll_top / self.max_top)
        for offset in range(thumb_height):
            self.canvas.put(
                x,
                layout.chat.y + top + offset,
                "█",
                self.theme.rose_dim,
            )

    def _placeholder(self) -> str:
        if self.ending:
            return "session closed"
        if self.choice_mode:
            return "choose a reply…"
        if self.streaming_index is not None:
            return "waiting for mia…"
        return ""

    def _footer_text(self) -> tuple[str, object]:
        if self.notice and time.monotonic() < self.notice_until:
            return self.notice, self.notice_style
        if self.closing_progress is not None:
            index, total = self.closing_progress
            return (
                f"closing connection  {index:02d} / {total:02d}  ·  enter skip",
                self.theme.red,
            )
        if self.ending:
            return "enter close the season  ·  ctrl+c leave", self.theme.faint
        if self.choice_mode:
            return (
                "↑↓ choose  ·  enter send  ·  1–n quick reply  ·  /help",
                self.theme.faint,
            )
        if self.streaming_index is not None:
            return "MIA is typing  ·  enter skip  ·  /help", self.theme.faint
        return (
            "/help commands  ·  pgup/pgdn scroll  ·  ctrl+c leave",
            self.theme.faint,
        )

    # ------------------------------------------------------------ primitives

    def set_status(self, status: str, label: str) -> None:
        self.status = status
        self.status_label = label

    def set_notice(self, text: str, tone: str = "warning") -> None:
        self.notice = text
        self.notice_style = self.theme.role(tone)
        self.notice_until = time.monotonic() + 3.2

    def _feed_editor(self, key) -> None:
        if key.name in {"char", "space"}:
            self.editor.insert(key.text or " ")
        elif key.name == "paste":
            self.editor.insert(key.text)
        elif key.name == "backspace":
            self.editor.backspace()
        elif key.name == "delete":
            self.editor.delete()
        elif key.name == "left":
            self.editor.left()
        elif key.name == "right":
            self.editor.right()
        elif key.name == "ctrl_left":
            self.editor.word_left()
        elif key.name == "ctrl_right":
            self.editor.word_right()
        elif key.name == "home":
            self.editor.home()
        elif key.name == "end":
            self.editor.end()
        elif key.name == "ctrl_a":
            self.editor.home()
        elif key.name == "ctrl_e":
            self.editor.end()
        elif key.name == "ctrl_u":
            self.editor.kill_to_start()
        elif key.name == "ctrl_k":
            self.editor.kill_to_end()
        elif key.name == "ctrl_w":
            self.editor.delete_word_before()
        elif key.name == "ctrl_d":
            self.editor.delete()
        elif key.name == "ctrl_l":
            self.canvas and self.canvas.invalidate()
        elif key.name == "ctrl_p":
            self.sidebar = not self.sidebar
        elif key.name == "up":
            self.editor.history_prev()
        elif key.name == "down":
            self.editor.history_next()

    def _global(self, key) -> bool:
        if key.name == "ctrl_c":
            raise ChatExit
        if key.name == "ctrl_l":
            if self.canvas is not None:
                self.canvas.invalidate()
            self.render()
            return True
        if key.name == "ctrl_p":
            self.sidebar = not self.sidebar
            self.render()
            return True
        if key.name == "f1":
            self._help_overlay()
            return True
        if (
            key.name == "char"
            and key.text == "?"
            and not self.editor.has_text
            and not self.choice_mode
        ):
            self._help_overlay()
            return True
        if key.name == "pageup":
            self._scroll_by(-max(1, self.viewport_height - 2))
            return True
        if key.name == "pagedown":
            self._scroll_by(max(1, self.viewport_height - 2))
            return True
        if key.name == "shift_up":
            self._scroll_by(-3)
            return True
        if key.name == "shift_down":
            self._scroll_by(3)
            return True
        if key.name == "mouse" and key.mouse and key.mouse.pressed:
            if key.mouse.wheel_up:
                self._scroll_by(-3)
                return True
            if key.mouse.wheel_down:
                self._scroll_by(3)
                return True
        return False

    def _scroll_by(self, delta: int) -> None:
        if self.max_top <= 0:
            return
        current = self.scroll_top if not self.pinned else self.max_top
        self.pinned = False
        self.scroll_top = min(self.max_top, max(0, current + delta))
        if self.scroll_top >= self.max_top:
            self.pinned = True
        self.render()

    def _poll(self, timeout: float):
        if self.terminal.take_resize():
            self.render()
        if self.terminal.should_terminate():
            raise ChatExit
        now = time.monotonic()
        if now >= self._next_spinner:
            self.spinner_index = (self.spinner_index + 1) % len(SPINNER)
            self._next_spinner = now + 0.08
        if self.notice and now >= self.notice_until:
            self.notice = ""
            self.render()
        key = self.terminal.read_key(timeout)
        if key is not None and key.name == "eof":
            raise ChatExit
        return key


def run_blocked(terminal: Terminal, theme: Theme) -> None:
    """Show the permanent block screen until the user closes it."""

    canvas: Canvas | None = None
    while True:
        if terminal.take_resize() or canvas is None:
            cols, rows = terminal.size()
            canvas = Canvas(cols, rows, theme)
        assert canvas is not None
        canvas.clear()
        components.draw_blocked(canvas, theme)
        terminal.write(canvas.render())
        while True:
            if terminal.take_resize():
                break
            if terminal.should_terminate():
                return
            key = terminal.read_key(0.2)
            if key is None:
                continue
            if key.name in {"eof", "enter", "esc", "q", "ctrl_c"}:
                return
