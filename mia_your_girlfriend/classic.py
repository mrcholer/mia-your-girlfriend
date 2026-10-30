"""The original line-by-line interface, preserved for scripts and --classic."""

from __future__ import annotations

import sys
import textwrap
import time
from pathlib import Path

from . import story


class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    PINK = "\033[95m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    WHITE = "\033[97m"


MOOD_COLORS = {
    "happy": Style.PINK,
    "soft": Style.CYAN,
    "hurt": Style.YELLOW,
    "angry": Style.RED,
    "blocked": Style.RED,
}
MOODS = {
    key: (glyph, label, MOOD_COLORS.get(key, Style.PINK))
    for key, (glyph, label) in story.MOODS.items()
}


class Game:
    """Classic choice-driven renderer with no external dependencies."""

    def __init__(self, color: bool, fast: bool) -> None:
        self.color = color
        self.fast = fast
        self.affection = 0
        self.trust = 0
        self.choices_made = 0

    def paint(self, text: str, shade: str) -> str:
        return f"{shade}{text}{Style.RESET}" if self.color else text

    def pause(self, seconds: float = 0.35) -> None:
        if not self.fast and sys.stdout.isatty():
            time.sleep(seconds)

    def say(self, text: str, shade: str | None = None) -> None:
        print(self.paint(text, shade) if shade else text)

    def header(self, episode: int = 0, mood: str = "happy") -> None:
        icon, status, _ = MOODS[mood]
        label = f"SEASON OF US  /  MIA {icon} {status.upper()}"
        if episode:
            label += f"  /  EP {episode:02d} OF 05"
        self.say(
            "╭─ " + label + " " + "─" * max(2, 62 - len(label)) + "╮",
            Style.PINK,
        )
        self.say(
            "│  a little story about love, late replies & almost forever      │",
            Style.DIM,
        )
        self.say("╰" + "─" * 68 + "╯", Style.PINK)

    def portrait(self, mood: str = "happy") -> None:
        _, _, shade = MOODS[mood]
        portrait_file = Path(__file__).with_name("mia_girl.txt")
        if portrait_file.is_file():
            try:
                rows = portrait_file.read_text(encoding="utf-8").splitlines()
            except OSError:
                rows = []
            if rows:
                for row in rows:
                    self.say("   " + row, shade)
                self.say("       ✦ your chat buddy ✦", Style.DIM)
                return

        # Last-resort monochrome portrait if package data is missing.
        art = [
            "                 .-._       _.-.",
            "             .-''    \\   /'    '-.",
            "           .'     .----\\_/----.      '.",
            "          /    .-'  _  BLACK BOW '-.    \\",
            "         /   .'   .' -.   .-' '.   '.   \\",
            "        |   /   .'      '-'      '.   \\   |",
            "        |  |  .'  .-~~~~~~~~~~~~-.  '.  |  |",
            "        |  | /  .'  /\\       /\\  '.  \\ |  |",
            "        |  | |  |  (◕)\\____/(◕)  |  | |  |",
            "        |  | |  |       .ω.       |  | |  |",
            "        |  |  \\  '.   '---'    .'  /  |  |",
            "         \\  '.  '-..-..____..-..-'  .'  /",
            "          '.  '-.  '--.____.--'  .-'  .'",
            "            '-._ '-.  ♡    ♡ .-' _.-'",
            "                '--.  M I A .--'",
            "                   /|  ♡♡  |\\",
            "                  /_|_______|_\\",
            "                    /       \\",
            "                   /_________\\",
        ]
        for row in art:
            self.say("   " + row, shade)
        self.say("       ✦ your chat buddy ✦", Style.DIM)

    def bubble(self, who: str, message: str, shade: str) -> None:
        width = 64
        self.say(
            f"╭─ {who} " + "─" * max(2, width - len(who) - 3) + "╮",
            shade,
        )
        for paragraph in message.splitlines() or [""]:
            for row in textwrap.wrap(paragraph, width=width - 4) or [""]:
                self.say(f"│  {row:<{width - 4}}  │", shade)
        self.say("╰" + "─" * width + "╯", shade)

    def choose(
        self,
        question: str,
        options: list[tuple[str, int, int]],
    ) -> tuple[int, int]:
        self.bubble("MIA", question, Style.CYAN)
        self.say("  REPLY WITH", Style.DIM)
        for idx, (answer, _, _) in enumerate(options, 1):
            self.say(f"  {self.paint(f'[{idx}]', Style.PINK)}  {answer}")
        while True:
            try:
                raw = input(self.paint("\n  you › ", Style.GREEN)).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self.say(
                    "  chat paused. Mia will be here if you want to return.",
                    Style.DIM,
                )
                raise SystemExit(0)
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                self.choices_made += 1
                answer, affection, trust = options[int(raw) - 1]
                self.bubble("YOU", answer, Style.GREEN)
                return affection, trust
            self.say("  choose a number from the reply list above.", Style.YELLOW)

    def scene(self, scene: story.Scene) -> None:
        print()
        self.header(scene.episode, scene.mood)
        self.say(f"\n  ✦  {scene.title}", Style.WHITE)
        self.portrait(scene.mood)
        options = [
            (choice.text, choice.affection, choice.trust)
            for choice in scene.choices
        ]
        affection, trust = self.choose(scene.question, options)
        self.affection += affection
        self.trust += trust
        self.pause()

    def mia(self, message: str) -> None:
        self.pause(0.25)
        self.bubble("MIA", message, Style.CYAN)

    def play(self) -> None:
        self.affection = self.trust = self.choices_made = 0
        self.header()
        self.portrait()
        self.say("\n  MIA is online.", Style.GREEN)
        self.mia(story.INTRO)

        for scene in story.SCENES:
            self.scene(scene)
            if scene.after:
                self.mia(scene.after)

        self.finale()

    def finale(self) -> None:
        print()
        self.header(5, "angry")
        self.say("\n  ✦  SEASON FINALE: THE PLATFORM", Style.RED)
        self.portrait("angry")
        self.mia(story.finale_last_words(self.affection, self.trust))
        self.pause(0.6)
        for message in story.FINALE_MESSAGES:
            self.mia(message)
        self.say("\n  " + story.FINALE_SIGNAL, Style.RED)
        self.say("  " + "─" * 62, Style.RED)
        for error in story.FINALE_ERRORS:
            self.say("  × " + error, Style.RED)
            self.pause(0.13)
        self.say(
            r"""
            .-''''-.             . . .
           /  ;  ;  \          .       .
          |    ︵    |     ♥  .    💔   .
           \  ___  /       .   .       .
            '.___.'            ' . . '""",
            Style.RED,
        )
        self.say(
            "\n  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
            Style.RED,
        )
        for line in story.RELATIONSHIP_STATUS:
            self.say(f"  ┃  {line:<54}┃", Style.RED)
        self.say(
            "  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
            Style.RED,
        )
        self.say(
            "  " + story.statistics(self.choices_made, self.affection, self.trust),
            Style.DIM,
        )
        self.say("\n  [ CLOSE SEASON ]", Style.RED)


def print_blocked(game: Game) -> None:
    game.header(mood="angry")
    game.bubble("MIA · BLOCKED", story.BLOCKED_MESSAGE, Style.RED)
    game.say(
        "\n  ACCESS DENIED — MIA IS STILL ANGRY AND HAS BLOCKED THIS CHAT.",
        Style.RED,
    )
    game.say("  RELATIONSHIP: CLOSED. THERE IS NO WAY BACK TOGETHER.", Style.RED)
    game.say("  A new season cannot be started from this installation.", Style.RED)
    game.say("  " + "─" * 62, Style.RED)
    for error in (
        "ERR 031  season state is permanently closed",
        "ERR 032  new-season request rejected",
        "ERR 033  contact remains blocked",
    ):
        game.say("  × " + error, Style.RED)
    game.say("\n  [ CHAT CLOSED ]", Style.RED)
