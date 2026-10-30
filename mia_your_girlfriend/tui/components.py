"""Chat transcript, chrome, overlays, and splash rendering."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import art
from .layout import Layout, Rect, option_wrap_width
from .render import Canvas, Span, display_width, pad, truncate, wrap_text
from .theme import EMPTY, Style, Theme


SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

WORDMARK = (
    "███╗   ███╗██╗ █████╗",
    "████╗ ████║██║██╔══██╗",
    "██╔████╔██║██║███████║",
    "██║╚██╔╝██║██║██╔══██║",
    "██║ ╚═╝ ██║██║██║  ██║",
    "╚═╝     ╚═╝╚═╝╚═╝  ╚═╝",
)


@dataclass(frozen=True)
class ChatEntry:
    speaker: str
    text: str


@dataclass(frozen=True)
class SystemEntry:
    text: str
    tone: str = "system"
    icon: str = "·"


@dataclass(frozen=True)
class SceneEntry:
    episode: int
    title: str
    finale: bool = False


@dataclass(frozen=True)
class RuleEntry:
    label: str = ""
    tone: str = "border"


@dataclass(frozen=True)
class BoxEntry:
    title: str
    lines: tuple[str, ...]
    tone: str = "red"


@dataclass(frozen=True)
class SpacerEntry:
    pass


Entry = ChatEntry | SystemEntry | SceneEntry | RuleEntry | BoxEntry | SpacerEntry
RenderLine = list[Span]


def blank() -> RenderLine:
    return [Span(" ")]


def build_lines(
    entries: list[Entry],
    width: int,
    theme: Theme,
    streaming_index: int | None = None,
    spinner: str = "⠋",
) -> list[RenderLine]:
    lines: list[RenderLine] = []
    for index, entry in enumerate(entries):
        if isinstance(entry, ChatEntry):
            lines.extend(
                _chat_lines(
                    entry,
                    width,
                    theme,
                    streaming=index == streaming_index,
                    spinner=spinner,
                )
            )
        elif isinstance(entry, SystemEntry):
            lines.extend(_system_lines(entry, width, theme))
        elif isinstance(entry, SceneEntry):
            lines.extend(_scene_lines(entry, width, theme))
        elif isinstance(entry, RuleEntry):
            lines.extend(_rule_lines(entry, width, theme))
        elif isinstance(entry, BoxEntry):
            lines.extend(_box_lines(entry, width, theme))
        elif isinstance(entry, SpacerEntry):
            lines.append(blank())
    return lines


def _chat_lines(
    entry: ChatEntry,
    width: int,
    theme: Theme,
    streaming: bool,
    spinner: str,
) -> list[RenderLine]:
    label = "MIA" if entry.speaker in {"mia", "assistant"} else "YOU"
    role_style = theme.mia if label == "MIA" else theme.user
    prefix = [
        Span("● ", role_style),
        Span(label, role_style.with_(bold=True)),
        Span("  ", EMPTY),
    ]
    body_width = max(8, width - 7)
    if streaming and entry.text:
        body_width = max(8, body_width - 1)
    if not entry.text:
        if streaming:
            body = [[Span(spinner + " ", role_style), Span("typing", theme.muted)]]
        else:
            body = [[Span("", theme.text)]]
    else:
        wrapped = wrap_text(entry.text, body_width)
        body = [[Span(part, theme.text)] for part in wrapped]
        if streaming:
            body[-1].append(Span("▌", theme.rose_bright))

    lines: list[RenderLine] = []
    for index, body_line in enumerate(body):
        if index == 0:
            lines.append(prefix + body_line)
        else:
            lines.append([Span(" " * 7, EMPTY)] + body_line)
    lines.append(blank())
    return lines


def _system_lines(entry: SystemEntry, width: int, theme: Theme) -> list[RenderLine]:
    style = theme.role(entry.tone)
    icon = entry.icon or "·"
    prefix = [Span(icon + " ", style), Span("", style)]
    body_width = max(8, width - 2)
    wrapped = wrap_text(entry.text, body_width)
    lines: list[RenderLine] = []
    for index, part in enumerate(wrapped):
        if index == 0:
            lines.append(prefix + [Span(part, style)])
        else:
            lines.append([Span("  ", EMPTY), Span(part, style)])
    if lines:
        lines[-1].append(Span("", style))
    if entry.text:
        lines.append(blank())
    return lines


def _scene_lines(entry: SceneEntry, width: int, theme: Theme) -> list[RenderLine]:
    label = "SEASON FINALE" if entry.finale else f"EPISODE {entry.episode:02d} / 05"
    label_style = theme.red_bright if entry.finale else theme.rose_dim
    title_style = theme.bright if not entry.finale else theme.red
    combined = label + "  ·  " + entry.title
    if display_width(combined) <= width:
        first = [
            Span(label, label_style.with_(bold=True)),
            Span("  ·  ", theme.faint),
            Span(entry.title, title_style.with_(bold=True)),
        ]
    else:
        first = [
            Span(label, label_style.with_(bold=True)),
            Span("  ·  ", theme.faint),
        ]
        second = [Span(entry.title, title_style.with_(bold=True))]
        lines = [first, second]
    if display_width(combined) <= width:
        lines = [first]
    lines.append([Span("─" * width, theme.rule)])
    lines.append(blank())
    return lines


def _rule_lines(entry: RuleEntry, width: int, theme: Theme) -> list[RenderLine]:
    tone = theme.role(entry.tone) if entry.tone != "border" else theme.border
    if entry.label:
        label = f" {entry.label} "
        line = [
            Span("──", tone),
            Span(label, theme.role(entry.tone)),
            Span("─" * max(0, width - 2 - display_width(label)), tone),
        ]
    else:
        line = [Span("─" * width, tone)]
    return [line, blank()]


def _box_lines(entry: BoxEntry, width: int, theme: Theme) -> list[RenderLine]:
    tone = theme.role(entry.tone)
    box_width = min(max(24, width), 80)
    inner = max(8, box_width - 4)
    content: list[str] = []
    for source in entry.lines:
        content.extend(wrap_text(source, inner))
    title = f" {entry.title} "
    top_fill = max(0, box_width - 3 - display_width(title))
    lines: list[RenderLine] = [
        [
            Span("╭─", tone),
            Span(title, tone.with_(bold=True)),
            Span("─" * top_fill + "╮", tone),
        ]
    ]
    for part in content:
        lines.append(
            [
                Span("│", tone),
                Span(" " + pad(part, inner) + " ", theme.text),
                Span("│", tone),
            ]
        )
    lines.append([Span("╰" + "─" * (box_width - 2) + "╯", tone)])
    lines.append(blank())
    return lines


def draw_line(canvas: Canvas, x: int, y: int, line: RenderLine, width: int) -> None:
    column = x
    limit = x + width
    for span in line:
        if column >= limit:
            break
        column = canvas.put(
            column,
            y,
            span.text,
            span.style,
            max_width=limit - column,
        )


def draw_header(
    canvas: Canvas,
    layout: Layout,
    theme: Theme,
    status: str,
    status_label: str,
    episode: int,
    total_episodes: int,
    spinner: str,
) -> None:
    heart = "♡" if status not in {"blocked", "closed", "angry"} else "×"
    canvas.put(1, 0, heart, theme.rose_bright if heart == "♡" else theme.red)
    canvas.put(3, 0, "mia", theme.rose_bright)
    x = 7
    if layout.cols >= 78:
        canvas.put(x, 0, "·  season of us", theme.muted)
        x += 16

    glyph, style = theme.status(status)
    if status == "typing":
        glyph = spinner
    status_text = f"{glyph} {status_label}"
    right = layout.cols - 1
    episode_text = f"EP {episode:02d} / {total_episodes:02d}"
    if layout.cols >= 86:
        canvas.put_right(right, 0, episode_text, theme.faint)
        right -= display_width(episode_text) + 3
    if layout.cols >= 52:
        canvas.put_right(right, 0, status_text, style)
    else:
        canvas.put_right(right, 0, glyph, style)

    canvas.hline(0, 1, layout.cols, "─", theme.rule)


def draw_sidebar(
    canvas: Canvas,
    layout: Layout,
    theme: Theme,
    status: str,
    status_label: str,
    mood_label: str,
    episode: int,
    total_episodes: int,
    replies: int,
    elapsed: str,
) -> None:
    sidebar = layout.sidebar
    if sidebar is None:
        return
    border_x = sidebar.x + sidebar.width - 1
    canvas.vline(border_x, sidebar.y, sidebar.height, "│", theme.border)
    x = sidebar.x + 3

    top = sidebar.y + 2
    for offset, row in enumerate(WORDMARK):
        canvas.put(x, top + offset, row, theme.rose)
    tagline_y = top + len(WORDMARK) + 1
    canvas.put(x, tagline_y, "your terminal girlfriend", theme.muted)
    canvas.hline(x, tagline_y + 2, sidebar.width - 6, "─", theme.rule)

    glyph, style = theme.status(status)
    if status == "typing":
        glyph = "●"
    y = tagline_y + 4
    canvas.put(x, y, glyph + " ", style)
    canvas.put(x + 2, y, status_label, style)
    canvas.put(x, y + 1, "mood", theme.faint)
    canvas.put(x + 7, y + 1, mood_label.lower(), theme.muted)

    y += 3
    canvas.put(x, y, "season 01", theme.faint)
    canvas.put(x, y + 1, "chapter", theme.faint)
    canvas.put(x + 10, y + 1, f"{episode:02d} / {total_episodes:02d}", theme.text)
    canvas.put(x, y + 2, "replies", theme.faint)
    canvas.put(x + 10, y + 2, f"{replies:02d}", theme.text)

    version_y = sidebar.y + sidebar.height - 1
    if version_y >= y + 4:
        canvas.put(x, y + 3, "session", theme.faint)
        canvas.put(x + 10, y + 3, elapsed, theme.text)

    if sidebar.height >= 28:
        hint_y = sidebar.y + sidebar.height - 7
        canvas.hline(x, hint_y - 1, sidebar.width - 6, "─", theme.rule)
        hints = (
            ("/help", "commands"),
            ("^P", "sidebar"),
            ("^C", "leave"),
        )
        for offset, (key, label) in enumerate(hints):
            canvas.put(x, hint_y + offset, key, theme.rose_dim)
            canvas.put(x + 8, hint_y + offset, label, theme.faint)

    canvas.put(x, version_y, "mia 2.0", theme.faint)
    canvas.put_right(
        border_x - 2,
        version_y,
        "local",
        theme.faint,
    )


def wrap_options(options: list[object], width: int) -> list[list[str]]:
    wrap_width = option_wrap_width(width)
    return [wrap_text(getattr(option, "text", str(option)), wrap_width) for option in options]


def option_line_count(wrapped: list[list[str]]) -> int:
    return sum(max(1, len(lines)) for lines in wrapped)


def draw_options(
    canvas: Canvas,
    layout: Layout,
    theme: Theme,
    options: list[object],
    wrapped: list[list[str]],
    selected: int,
) -> None:
    if layout.options is None or layout.option_label_y is None:
        return
    x = layout.content_x
    y = layout.option_label_y
    label = "reply"
    canvas.put(x, y, label, theme.rose_dim.with_(bold=True))
    hint = "↑↓ choose  ·  enter send"
    hint_x = x + layout.content_width - display_width(hint)
    if hint_x > x + 10:
        canvas.put(hint_x, y, hint, theme.faint)
    canvas.hline(
        x + display_width(label) + 2,
        y,
        max(0, layout.content_width - display_width(label) - 2),
        "─",
        theme.rule,
    )

    row = layout.options.y
    for index, lines in enumerate(wrapped):
        is_selected = index == selected
        style = theme.selection if is_selected else theme.text
        for line_index, text in enumerate(lines):
            if row >= layout.options.bottom:
                return
            if is_selected:
                canvas.fill(x, row, layout.content_width, 1, " ", theme.selection)
            if line_index == 0:
                prefix = (
                    f"› {index + 1}  " if is_selected else f"  {index + 1}  "
                )
                if is_selected:
                    canvas.put(x, row, prefix, theme.selection)
                else:
                    canvas.put(x + 2, row, str(index + 1), theme.rose_dim)
                    canvas.put(x + 4, row, "  ", EMPTY)
                canvas.put(x + 5, row, text, style)
            else:
                canvas.put(x + 5, row, text, style)
            row += 1


def draw_input(
    canvas: Canvas,
    layout: Layout,
    theme: Theme,
    editor: object,
    enabled: bool,
    placeholder: str = "",
) -> None:
    x = layout.content_x
    y = layout.input_y
    canvas.hline(x, layout.rule_y, layout.content_width, "─", theme.rule)
    if not enabled:
        canvas.put(x, y, "·", theme.faint)
        if placeholder:
            canvas.put(x + 2, y, truncate(placeholder, layout.content_width - 2), theme.faint)
        return

    canvas.put(x, y, "you", theme.green.with_(bold=True))
    canvas.put(x + 4, y, "›", theme.green)
    prompt_width = 6
    available = max(1, layout.content_width - prompt_width)
    visible, cursor_column, _clipped, start = editor.window(available)
    text_x = x + prompt_width
    if not visible and placeholder:
        canvas.put(text_x, y, truncate(placeholder, available), theme.faint)

    if visible:
        canvas.put(text_x, y, visible, theme.text)
    cursor_x = text_x + cursor_column
    cursor_index = editor.cursor
    if start <= cursor_index < start + len(visible):
        char = editor.text[cursor_index]
        canvas.put(cursor_x, y, char, theme.cursor)
    else:
        canvas.put(cursor_x, y, " ", theme.cursor)


def draw_footer(
    canvas: Canvas,
    layout: Layout,
    theme: Theme,
    left: str,
    left_style: Style | None = None,
    right: str = "",
) -> None:
    y = layout.footer_y
    x = layout.content_x
    width = layout.content_width
    style = left_style or theme.faint
    if right and display_width(right) + 3 < width:
        canvas.put_right(x + width, y, right, theme.faint)
        width -= display_width(right) + 3
    canvas.put(x, y, truncate(left, width), style)


def draw_splash(canvas: Canvas, theme: Theme, first_run: bool) -> None:
    cols, rows = canvas.width, canvas.height
    if cols < 44 or rows < 14:
        draw_too_small(canvas, theme, suffix="q quit")
        return

    if cols >= 78 and rows >= 24:
        _draw_splash_wide(canvas, theme, first_run)
    else:
        _draw_splash_compact(canvas, theme, first_run)


def _draw_splash_wide(canvas: Canvas, theme: Theme, first_run: bool) -> None:
    cols, rows = canvas.width, canvas.height
    portrait = art.girl_lines()
    art_width = max(display_width(line) for line in portrait)
    right_width = 36
    gap = 3
    total = art_width + gap + right_width
    left_x = max(2, (cols - total) // 2)
    art_top = max(1, (rows - len(portrait)) // 2)
    right_x = left_x + art_width + gap
    right_top = art_top

    for offset, line in enumerate(portrait):
        canvas.put(left_x, art_top + offset, line, theme.rose)

    for offset, line in enumerate(WORDMARK):
        canvas.put(right_x, right_top + offset, line, theme.rose_bright)
    y = right_top + len(WORDMARK) + 1
    canvas.put(right_x, y, "your terminal girlfriend", theme.muted)
    y += 2
    canvas.hline(right_x, y, right_width, "─", theme.rule)
    y += 2
    for line in wrap_text(
        "a little story about love, late replies & almost forever", right_width
    ):
        canvas.put(right_x, y, line, theme.text)
        y += 1

    y += 1
    canvas.put(right_x, y, "SEASON 01 · FIVE CHAPTERS", theme.rose_dim)
    y += 2
    keys = (
        ("enter", "begin the season"),
        ("p", "view portrait"),
        ("?", "keys & commands"),
        ("q", "leave"),
    )
    for key, label in keys:
        canvas.put(right_x, y, key, theme.rose_bright)
        canvas.put(right_x + 8, y, label, theme.muted)
        y += 1

    hint = "ctrl+c exits at any time" if first_run else "press enter to continue"
    canvas.put_center(0, rows - 2, cols, hint, theme.faint)


def _draw_splash_compact(canvas: Canvas, theme: Theme, first_run: bool) -> None:
    cols, rows = canvas.width, canvas.height
    block_height = len(WORDMARK) + 12
    top = max(1, (rows - block_height) // 2)
    wordmark_width = max(display_width(line) for line in WORDMARK)
    x = max(2, (cols - wordmark_width) // 2)
    for offset, line in enumerate(WORDMARK):
        canvas.put(x, top + offset, line, theme.rose_bright)
    y = top + len(WORDMARK) + 1
    canvas.put_center(0, y, cols, "your terminal girlfriend", theme.muted)
    y += 2
    canvas.hline(max(2, (cols - 36) // 2), y, min(36, cols - 4), "─", theme.rule)
    y += 2
    for line in wrap_text(
        "a little story about love, late replies & almost forever", max(20, cols - 8)
    ):
        canvas.put_center(0, y, cols, line, theme.text)
        y += 1
    y += 1
    canvas.put_center(0, y, cols, "SEASON 01 · FIVE CHAPTERS", theme.rose_dim)
    y += 2
    canvas.put_center(0, y, cols, "enter begin  ·  p portrait", theme.muted)
    y += 1
    canvas.put_center(0, y, cols, "? keys  ·  q leave", theme.muted)
    if first_run:
        canvas.put_center(0, rows - 2, cols, "ctrl+c exits at any time", theme.faint)


def draw_too_small(canvas: Canvas, theme: Theme, suffix: str = "") -> None:
    cols, rows = canvas.width, canvas.height
    y = max(0, rows // 2 - 2)
    canvas.put_center(0, y, cols, "terminal too small", theme.bright)
    canvas.put_center(
        0,
        y + 1,
        cols,
        "resize to at least 44 × 14",
        theme.muted,
    )
    canvas.put_center(0, y + 2, cols, f"current size: {cols} × {rows}", theme.faint)
    if suffix:
        canvas.put_center(0, y + 4, cols, suffix, theme.rose_dim)


def draw_help(canvas: Canvas, theme: Theme, scroll: int = 0) -> None:
    cols, rows = canvas.width, canvas.height
    width = min(76, max(36, cols - 4))
    compact = width < 60
    content = (
        [
            "CHAT",
            "  enter         send reply / skip typing",
            "  ↑ ↓           choose reply / move cursor",
            "  1–3           quick reply",
            "  pgup / pgdn   scroll chat",
            "  ctrl+u / d    scroll half a page",
            "  home / end    top / bottom",
            "  mouse wheel   scroll chat",
            "  ctrl+p        toggle sidebar",
            "  ctrl+l        redraw",
            "",
            "COMMANDS",
            "  /help         keys & commands",
            "  /status       session status",
            "  /portrait     Mia's portrait",
            "  /portrait legacy   original ANSI art",
            "  /clear        clear the visible chat",
            "  /about        about this season",
            "  /quit         leave the chat",
        ]
        if not compact
        else [
            "CHAT",
            "  enter   send / skip",
            "  ↑ ↓     choose reply",
            "  pgup    scroll chat",
            "  ctrl+p  sidebar",
            "  ctrl+l  redraw",
            "",
            "COMMANDS",
            "  /help  /status  /portrait",
            "  /clear  /about  /quit",
        ]
    )
    height = len(content) + 4
    height = min(height, max(8, rows - 2))
    x = max(1, (cols - width) // 2)
    y = max(1, (rows - height) // 2)
    canvas.fill(x, y, width, height, " ", theme.overlay)
    canvas.box(x, y, width, height, theme.rose_dim, " keys & commands ")
    visible = height - 4
    line_y = y + 2
    for line in content[scroll : scroll + visible]:
        style = theme.rose_dim if line in {"CHAT", "COMMANDS"} else theme.text
        if line == "":
            line_y += 1
            continue
        canvas.put(x + 2, line_y, truncate(line, width - 4), style)
        line_y += 1
    canvas.put_center(x, y + height - 2, width, "esc closes this panel", theme.faint)


def draw_portrait(
    canvas: Canvas,
    theme: Theme,
    scroll: int = 0,
    legacy: bool = False,
) -> None:
    cols, rows = canvas.width, canvas.height
    canvas.put_center(0, 1, cols, "mia · portrait", theme.rose_dim)
    if legacy:
        lines = art.legacy_ansi_lines(theme)
    else:
        lines = [[Span(line, theme.rose)] for line in art.girl_lines()]
    if not lines:
        canvas.put_center(0, rows // 2, cols, "portrait unavailable", theme.faint)
        return
    art_height = len(lines)
    view_height = max(1, rows - 4)
    max_scroll = max(0, art_height - view_height)
    scroll = min(max(0, scroll), max_scroll)
    art_width = max(
        (sum(display_width(span.text) for span in line) for line in lines),
        default=0,
    )
    x = max(0, (cols - art_width) // 2)
    for index, line in enumerate(lines[scroll : scroll + view_height]):
        draw_line(canvas, x, 3 + index, line, cols)
    right = "↑↓ scroll  ·  esc close" if max_scroll else "esc close"
    canvas.put_center(0, rows - 1, cols, right, theme.faint)


def draw_blocked(canvas: Canvas, theme: Theme) -> None:
    from .. import story

    cols, rows = canvas.width, canvas.height
    canvas.put(1, 0, "×", theme.red)
    canvas.put(3, 0, "mia", theme.red)
    canvas.put(8, 0, "·  season closed", theme.muted)
    canvas.put_right(cols - 1, 0, "× blocked", theme.red)
    canvas.hline(0, 1, cols, "─", theme.rule)

    width = min(72, max(36, cols - 4))
    body_width = width - 4
    content: list[str] = []
    content.extend(wrap_text(story.BLOCKED_MESSAGE, body_width))
    content.extend(["", "ACCESS DENIED"])
    content.append("Relationship: closed. There is no way back together.")
    content.append("A new season cannot be started from this installation.")
    content.extend(
        (
            "",
            "ERR 031  season state is permanently closed",
            "ERR 032  new-season request rejected",
            "ERR 033  contact remains blocked",
        )
    )
    height = len(content) + 4
    height = min(height, max(8, rows - 4))
    x = max(1, (cols - width) // 2)
    y = max(2, (rows - height) // 2)
    canvas.fill(x, y, width, height, " ", theme.overlay)
    canvas.box(x, y, width, height, theme.red, " mia · blocked ")
    line_y = y + 2
    for line in content[: height - 4]:
        style = theme.red if line.startswith("ERR") else theme.text
        if line == "ACCESS DENIED":
            style = theme.red_bright
        canvas.put(x + 2, line_y, truncate(line, body_width), style)
        line_y += 1
    canvas.put_center(0, rows - 2, cols, "[ enter to close ]", theme.red)
