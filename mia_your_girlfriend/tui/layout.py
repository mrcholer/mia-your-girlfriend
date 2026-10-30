"""Responsive geometry for the chat screen."""

from __future__ import annotations

from dataclasses import dataclass


SIDEBAR_WIDTH = 30
MIN_WIDTH = 44
MIN_HEIGHT = 14


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


@dataclass(frozen=True)
class Layout:
    cols: int
    rows: int
    too_small: bool
    sidebar: Rect | None
    main: Rect
    chat: Rect
    content_x: int
    content_width: int
    scrollbar_x: int | None
    option_label_y: int | None
    options: Rect | None
    rule_y: int
    input_y: int
    footer_y: int
    show_sidebar: bool

    @property
    def sidebar_visible(self) -> bool:
        return self.sidebar is not None


def compute_layout(
    cols: int,
    rows: int,
    sidebar_requested: bool,
    option_lines: int = 0,
) -> Layout:
    cols = max(1, cols)
    rows = max(1, rows)

    show_sidebar = (
        sidebar_requested
        and cols >= 100
        and rows >= 22
        and not (cols < MIN_WIDTH or rows < MIN_HEIGHT)
    )
    sidebar = (
        Rect(0, 2, SIDEBAR_WIDTH, max(0, rows - 2)) if show_sidebar else None
    )
    main_x = SIDEBAR_WIDTH if show_sidebar else 0
    main_width = max(1, cols - main_x)
    main = Rect(main_x, 2, main_width, max(0, rows - 2))

    if main_width >= 32:
        content_width = min(96, max(10, main_width - 6))
        content_x = main_x + max(2, (main_width - content_width) // 2)
        scrollbar_x = main_x + main_width - 2
    else:
        content_width = max(8, main_width - 2)
        content_x = main_x + 1
        scrollbar_x = None

    footer_y = rows - 1
    input_y = rows - 2
    rule_y = rows - 3

    has_options = option_lines > 0
    if has_options:
        option_label_y = rule_y - option_lines - 1
        options_y = rule_y - option_lines
        options = Rect(content_x, options_y, content_width, option_lines)
        chat_bottom = option_label_y - 1
    else:
        option_label_y = None
        options = None
        chat_bottom = rule_y - 1

    chat_height = max(0, chat_bottom - 2)
    chat = Rect(content_x, 2, content_width, chat_height)

    too_small = (
        cols < MIN_WIDTH
        or rows < MIN_HEIGHT
        or chat_height < 3
        or (has_options and option_label_y is not None and option_label_y <= 2)
    )

    return Layout(
        cols=cols,
        rows=rows,
        too_small=too_small,
        sidebar=sidebar,
        main=main,
        chat=chat,
        content_x=content_x,
        content_width=content_width,
        scrollbar_x=scrollbar_x,
        option_label_y=option_label_y,
        options=options,
        rule_y=rule_y,
        input_y=input_y,
        footer_y=footer_y,
        show_sidebar=show_sidebar,
    )


def option_wrap_width(content_width: int) -> int:
    return max(8, content_width - 7)
