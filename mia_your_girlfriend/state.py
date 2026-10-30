"""Permanent, per-installation season state.

The one-way season lock is deliberately preserved.  The TUI and the classic
interface share this module so an ending in either mode is permanent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


APP_DIR = "MiaYourGirlfriend"
LOCK_TEXT = "Season 01 ended. Mia blocked this chat.\n"


@dataclass(frozen=True)
class StatePaths:
    lock_files: tuple[Path, ...]
    welcome_file: Path

    def is_closed(self) -> bool:
        return any(path.is_file() for path in self.lock_files)

    def migrate_legacy_lock(self) -> None:
        """If any lock exists, make every known location reflect it.

        This preserves the original behaviour that an older project-local lock
        keeps working after the package moves to per-user state.
        """

        if not self.is_closed():
            return
        for path in self.lock_files:
            _best_effort_write(path, LOCK_TEXT)

    def close_season(self) -> tuple[bool, list[OSError]]:
        failures: list[OSError] = []
        for path in self.lock_files:
            try:
                _write(path, LOCK_TEXT)
            except OSError as error:
                failures.append(error)
        return any(path.is_file() for path in self.lock_files), failures

    def welcome_seen(self) -> bool:
        return self.welcome_file.is_file()

    def remember_welcome(self) -> None:
        _best_effort_write(self.welcome_file, "1\n")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _best_effort_write(path: Path, text: str) -> None:
    try:
        _write(path, text)
    except OSError:
        pass


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / APP_DIR


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def paths() -> StatePaths:
    lock_files = [data_dir() / "season_closed"]
    root = project_root()
    if (root / "pyproject.toml").is_file():
        lock_files.append(root / ".season_closed")
    return StatePaths(tuple(lock_files), data_dir() / "seen_welcome")
