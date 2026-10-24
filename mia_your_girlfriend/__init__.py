#!/usr/bin/env python3
"""A chat-style, choice-driven terminal romance. Python 3.10+, no dependencies."""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path


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


MOODS = {
    "happy": ("✿", "Online", Style.PINK),
    "soft": ("♡", "Daydreaming", Style.CYAN),
    "hurt": ("…", "Quiet", Style.YELLOW),
    "angry": ("!", "Angry", Style.RED),
}


@dataclass
class Game:
    color: bool
    fast: bool
    affection: int = 0
    trust: int = 0
    choices_made: int = 0

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
        self.say("╭─ " + label + " " + "─" * max(2, 62 - len(label)) + "╮", Style.PINK)
        self.say("│  a little story about love, late replies & almost forever      │", Style.DIM)
        self.say("╰" + "─" * 68 + "╯", Style.PINK)

    def portrait(self, mood: str = "happy") -> None:
        _, _, shade = MOODS[mood]
        portrait_file = Path(__file__).with_name("mia_portrait.ans")
        if self.color and portrait_file.is_file():
            print(portrait_file.read_text(encoding="utf-8"), end="")
            return
        # Monochrome fallback for terminals where ANSI color is disabled.
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
        self.say(f"╭─ {who} " + "─" * max(2, width - len(who) - 3) + "╮", shade)
        for paragraph in message.splitlines() or [""]:
            for row in textwrap.wrap(paragraph, width=width - 4) or [""]:
                self.say(f"│  {row:<{width - 4}}  │", shade)
        self.say("╰" + "─" * width + "╯", shade)

    def choose(self, question: str, options: list[tuple[str, int, int]]) -> tuple[int, int]:
        self.bubble("MIA", question, Style.CYAN)
        self.say("  REPLY WITH", Style.DIM)
        for idx, (answer, _, _) in enumerate(options, 1):
            self.say(f"  {self.paint(f'[{idx}]', Style.PINK)}  {answer}")
        while True:
            try:
                raw = input(self.paint("\n  you › ", Style.GREEN)).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self.say("  chat paused. Mia will be here if you want to return.", Style.DIM)
                raise SystemExit(0)
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                self.choices_made += 1
                answer, affection, trust = options[int(raw) - 1]
                self.bubble("YOU", answer, Style.GREEN)
                return affection, trust
            self.say("  choose a number from the reply list above.", Style.YELLOW)

    def scene(self, episode: int, title: str, question: str, options: list[tuple[str, int, int]], mood: str = "happy") -> None:
        print()
        self.header(episode, mood)
        self.say(f"\n  ✦  {title}", Style.WHITE)
        self.portrait(mood)
        affection, trust = self.choose(question, options)
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
        self.mia("Hey! You made it. I was starting to think the rain scared you away.")

        self.scene(1, "THE MEET-CUTE", "It's raining outside the little bookshop. Mia holds out one umbrella. What do you say?", [
            ("Only if you pick the music on the way home.", 2, 1),
            ("Thanks. You look like you could use it more.", 1, 2),
            ("I was hoping you'd show up.", 2, 0),
        ])
        self.mia("Okay, stranger. You can walk with me. Just don't step in every puddle.")

        self.scene(2, "THE LITTLE THINGS", "Mia tells you about a dream she is afraid to chase. How do you answer?", [
            ("Tell me the whole dream. I'll listen.", 1, 2),
            ("Let's make a plan and try one small step.", 2, 2),
            ("Dreams are nice, but be realistic.", -1, -1),
        ], "soft")
        self.mia("I don't tell many people that. I'm glad you asked.")

        self.scene(3, "THE MISSED CALL", "You forgot to call when you said you would. Mia is quiet. What now?", [
            ("Own it. Apologize without an excuse.", 0, 2),
            ("Make a joke and hope she lets it go.", 1, -1),
            ("Say she's overreacting.", -2, -2),
        ], "soft")
        self.mia("I don't need perfect. I need to know I can count on you.")

        self.scene(4, "THE DISTANCE", "Lately your conversations have felt shorter. Mia asks, 'Are we okay?'", [
            ("Ask what she's been feeling, then really listen.", 1, 2),
            ("Say 'of course' and change the subject.", 0, -2),
            ("Tell her you're busy and end the call.", -1, -2),
        ], "hurt")
        self.mia("I keep trying to find us in the quiet. I don't know if you can hear me anymore.")

        self.scene(5, "THE LAST NIGHT", "Mia meets you beneath the old station clock. Her eyes are wet. What do you say?", [
            ("Tell her you love her, and ask what she needs.", 2, 2),
            ("Ask her to stay, but promise nothing will change.", 1, -1),
            ("Say nothing. You can't find the words.", -1, -1),
        ], "hurt")
        self.finale()

    def finale(self) -> None:
        print()
        self.header(5, "angry")
        self.say("\n  ✦  SEASON FINALE: THE PLATFORM", Style.RED)
        self.portrait("angry")
        if self.trust >= 4:
            last_words = "You did listen sometimes. That's what makes this so hard."
        elif self.affection >= 4:
            last_words = "I know there was love here. I just can't live on almost."
        else:
            last_words = "I waited for us to feel like us again. I can't wait anymore."
        self.mia(last_words)
        self.pause(0.6)
        self.mia("And I'm angry with you. I kept asking you to hear me, and you kept making me ask. You hurt me, and I'm done.")
        self.mia("We're over. I've blocked you. There is no way back together, and I don't want you to contact me again.")
        self.say("\n  [ LINK LOST ]  [ SESSION DESYNC ]  [ HEARTBEAT: NO RESPONSE ]", Style.RED)
        self.say("  " + "─" * 62, Style.RED)
        errors = [
            "ERR 001  heartbeat.service returned no response",
            "ERR 002  chat socket closed by remote user",
            "ERR 003  incoming messages disabled",
            "ERR 004  outgoing messages rejected",
            "ERR 005  contact route permanently blocked",
            "ERR 006  reconnect request denied",
            "ERR 007  alternate route lookup forbidden",
            "ERR 008  relationship state: CLOSED",
            "ERR 009  shared future reference not found",
            "ERR 010  plans database returned an empty result",
            "ERR 011  saved voice note unavailable",
            "ERR 012  favorite contact is no longer reachable",
            "ERR 013  read receipt service disconnected",
            "ERR 014  typing indicator will not return",
            "ERR 015  last-seen status removed",
            "ERR 016  memory cache overflow",
            "ERR 017  'we' could not be resolved",
            "ERR 018  heart.service failed to restore backup",
            "ERR 019  apology queued after channel closure",
            "ERR 020  delivery failed: this chat is blocked",
            "ERR 021  unblock request denied",
            "ERR 022  reunion endpoint does not exist",
            "ERR 023  second chance service unavailable",
            "ERR 024  undo operation not supported",
            "ERR 025  season continuation refused",
            "ERR 026  no further messages will be delivered",
            "ERR 027  final goodbye acknowledged",
            "ERR 028  session key destroyed",
            "ERR 029  reconnect disabled permanently",
            "ERR 030  chat archived — there is no way back",
            "ERR 031  anger cannot be talked away",
            "ERR 032  reunion request refused",
            "ERR 033  relationship lock cannot be reversed",
        ]
        for error in errors:
            self.say("  × " + error, Style.RED)
            self.pause(0.13)
        self.say(r"""
            .-''''-.             . . .
           /  ;  ;  \          .       .
          |    ︵    |     ♥  .    💔   .
           \  ___  /       .   .       .
            '.___.'            ' . . '""", Style.RED)
        self.say("\n  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓", Style.RED)
        self.say("  ┃  RELATIONSHIP: CLOSED     CHAT: BLOCKED              ┃", Style.RED)
        self.say("  ┃  RECONNECT: DENIED        NEW SEASON: BLOCKED       ┃", Style.RED)
        self.say("  ┃  SEASON 01: END                                     ┃", Style.RED)
        self.say("  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛", Style.RED)
        self.say(f"  replies: {self.choices_made}  ·  affection: {self.affection:+d}  ·  trust: {self.trust:+d}", Style.DIM)
        self.say("\n  [ CLOSE SEASON ]", Style.RED)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="A chat-style terminal romance with a cute anime-inspired portrait.")
    color_options = parser.add_mutually_exclusive_group()
    color_options.add_argument("--color", action="store_true", help="force the colored anime portrait even if NO_COLOR is set")
    color_options.add_argument("--no-color", action="store_true", help="disable terminal colors")
    parser.add_argument("--fast", action="store_true", help="skip pauses")
    args = parser.parse_args()
    if os.name == "nt":
        os.system("")  # Enable ANSI colors in modern Windows terminals.
    # Modern terminal emulators (including PowerShell) support ANSI by default.
    # Keep it on for the chat UI unless the user explicitly opts out.
    color = args.color or (not args.no_color and "NO_COLOR" not in os.environ)
    game = Game(color=color, fast=args.fast)
    package_root = Path(__file__).resolve().parent
    project_root = package_root.parent
    user_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    persistent_state = user_data / "MiaYourGirlfriend" / "season_closed"
    state_files = [persistent_state]
    project_state = project_root / ".season_closed"
    if (project_root / "pyproject.toml").is_file():
        state_files.append(project_state)

    if any(path.is_file() for path in state_files):
        # Migrate an older project-local lock into per-user app data. The lock
        # then survives moving, reinstalling, or recloning this project.
        for path in state_files:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Season 01 ended. Mia blocked this chat.\n", encoding="utf-8")
            except OSError:
                pass
        game.header(mood="angry")
        game.bubble(
            "MIA · BLOCKED",
            "I'm still angry about how you treated me. We're over, and there is no way back together. Do not contact me again.",
            Style.RED,
        )
        game.say("\n  ACCESS DENIED — MIA IS STILL ANGRY AND HAS BLOCKED THIS CHAT.", Style.RED)
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
        return
    game.play()
    failures = []
    for path in state_files:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Season 01 ended. Mia blocked this chat.\n", encoding="utf-8")
        except OSError as error:
            failures.append(error)
    if failures and not any(path.is_file() for path in state_files):
        game.say(f"\n  ERR 034  unable to save permanent block: {failures[0]}", Style.RED)
        raise SystemExit(1)
    game.say("\n  chat ended. take care of your heart. ♡", Style.DIM)


if __name__ == "__main__":
    main()
