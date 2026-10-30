"""Command-line dispatch for the classic and interactive interfaces."""

from __future__ import annotations

import argparse
import os
import sys
import traceback

from . import state, story
from ._version import __version__
from .classic import Game, Style, print_blocked
from .tui.app import MiaApp, Outcome, run_blocked
from .tui.terminal import Terminal
from .tui.theme import Theme


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mia",
        description=(
            "A chat-style terminal romance with a polished interactive TUI "
            "and a classic line-by-line mode."
        ),
    )
    color_options = parser.add_mutually_exclusive_group()
    color_options.add_argument(
        "--color",
        action="store_true",
        help="force terminal colors even if NO_COLOR is set",
    )
    color_options.add_argument(
        "--no-color",
        action="store_true",
        help="disable terminal colors",
    )
    parser.add_argument("--fast", action="store_true", help="skip pauses and typing")
    parser.add_argument(
        "--classic",
        action="store_true",
        help="use the original line-by-line interface",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args(argv)
    if os.name == "nt":
        os.system("")  # Enable ANSI processing in modern Windows terminals.

    color = args.color or (
        not args.no_color and "NO_COLOR" not in os.environ
    )
    state_paths = state.paths()
    state_paths.migrate_legacy_lock()

    interactive = _can_use_tui() and not args.classic
    if state_paths.is_closed():
        if interactive:
            _run_blocked_tui(color)
        else:
            print_blocked(Game(color=color, fast=args.fast))
        return

    if interactive:
        _run_tui(color=color, fast=args.fast, state_paths=state_paths)
        return

    game = Game(color=color, fast=args.fast)
    game.play()
    saved, failures = state_paths.close_season()
    if not saved:
        detail = failures[0] if failures else "unknown error"
        game.say(
            f"\n  ERR 034  unable to save permanent block: {detail}",
            Style.RED,
        )
        raise SystemExit(1)
    game.say("\n  chat ended. take care of your heart. ♡", Style.DIM)


def _can_use_tui() -> bool:
    return (
        sys.stdin.isatty()
        and sys.stdout.isatty()
        and os.environ.get("TERM", "").lower() != "dumb"
    )


def _run_tui(color: bool, fast: bool, state_paths: state.StatePaths) -> None:
    theme = Theme(enabled=color)
    first_run = not state_paths.welcome_seen()
    outcome = Outcome()
    error: BaseException | None = None
    try:
        with Terminal() as terminal:
            app = MiaApp(
                terminal=terminal,
                theme=theme,
                state_paths=state_paths,
                fast=fast,
                first_run=first_run,
            )
            outcome = app.run()
    except KeyboardInterrupt:
        outcome = Outcome(quit_early=True)
    except Exception as exc:  # The terminal is already restored by the context.
        error = exc

    if error is not None:
        _print_crash(error)
        raise SystemExit(1)

    if outcome.completed:
        _print_dim("\n  chat ended. take care of your heart. ♡", color)
        if outcome.exit_code:
            _print_color(
                "  mia: the season ended, but the permanent block could not be saved.",
                color,
                "red",
            )
            raise SystemExit(outcome.exit_code)
    else:
        _print_dim(
            "\n  chat paused. Mia will be here if you want to return.",
            color,
        )


def _run_blocked_tui(color: bool) -> None:
    theme = Theme(enabled=color)
    try:
        with Terminal() as terminal:
            run_blocked(terminal, theme)
    except KeyboardInterrupt:
        return
    except Exception as exc:
        _print_crash(exc)
        raise SystemExit(1)


def _print_crash(error: BaseException) -> None:
    print(
        "mia: the interactive interface hit an unexpected error.",
        file=sys.stderr,
    )
    if os.environ.get("MIA_DEBUG"):
        traceback.print_exception(type(error), error, error.__traceback__)
    else:
        print(f"  {type(error).__name__}: {error}", file=sys.stderr)
        print(
            "  try `mia --classic` for the line-by-line interface.",
            file=sys.stderr,
        )


def _print_dim(text: str, color: bool) -> None:
    if color:
        print(f"{Style.DIM}{text}{Style.RESET}")
    else:
        print(text)


def _print_color(text: str, color: bool, tone: str) -> None:
    if color:
        shade = Style.RED if tone == "red" else Style.DIM
        print(f"{shade}{text}{Style.RESET}")
    else:
        print(text)
