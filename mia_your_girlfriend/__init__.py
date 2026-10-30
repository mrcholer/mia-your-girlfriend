#!/usr/bin/env python3
"""A chat-style, choice-driven terminal romance with a polished TUI."""

from __future__ import annotations

from ._version import __version__
from .classic import MOODS, Game, Style
from .cli import main

__all__ = ["Game", "MOODS", "Style", "__version__", "main"]
