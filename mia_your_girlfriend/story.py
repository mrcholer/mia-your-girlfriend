"""Story content shared by the classic and interactive interfaces.

The text and choice effects here are the source of truth. Views only decide how
to present them, which keeps the original season intact when the UI changes.
"""

from __future__ import annotations

from dataclasses import dataclass


MOODS = {
    "happy": ("✿", "Online"),
    "soft": ("♡", "Daydreaming"),
    "hurt": ("…", "Quiet"),
    "angry": ("!", "Angry"),
    "blocked": ("×", "Blocked"),
}
"""Mood key -> (glyph, short label)."""


@dataclass(frozen=True)
class Choice:
    """One reply the player can select."""

    text: str
    affection: int
    trust: int


@dataclass(frozen=True)
class Scene:
    """A chapter question, its replies, and Mia's follow-up."""

    episode: int
    title: str
    question: str
    choices: tuple[Choice, ...]
    mood: str
    after: str | None = None


INTRO = "Hey! You made it. I was starting to think the rain scared you away."


SCENES: tuple[Scene, ...] = (
    Scene(
        episode=1,
        title="THE MEET-CUTE",
        question=(
            "It's raining outside the little bookshop. Mia holds out one "
            "umbrella. What do you say?"
        ),
        choices=(
            Choice("Only if you pick the music on the way home.", 2, 1),
            Choice("Thanks. You look like you could use it more.", 1, 2),
            Choice("I was hoping you'd show up.", 2, 0),
        ),
        mood="happy",
        after="Okay, stranger. You can walk with me. Just don't step in every puddle.",
    ),
    Scene(
        episode=2,
        title="THE LITTLE THINGS",
        question=(
            "Mia tells you about a dream she is afraid to chase. How do you answer?"
        ),
        choices=(
            Choice("Tell me the whole dream. I'll listen.", 1, 2),
            Choice("Let's make a plan and try one small step.", 2, 2),
            Choice("Dreams are nice, but be realistic.", -1, -1),
        ),
        mood="soft",
        after="I don't tell many people that. I'm glad you asked.",
    ),
    Scene(
        episode=3,
        title="THE MISSED CALL",
        question=(
            "You forgot to call when you said you would. Mia is quiet. What now?"
        ),
        choices=(
            Choice("Own it. Apologize without an excuse.", 0, 2),
            Choice("Make a joke and hope she lets it go.", 1, -1),
            Choice("Say she's overreacting.", -2, -2),
        ),
        mood="soft",
        after="I don't need perfect. I need to know I can count on you.",
    ),
    Scene(
        episode=4,
        title="THE DISTANCE",
        question=(
            "Lately your conversations have felt shorter. Mia asks, 'Are we okay?'"
        ),
        choices=(
            Choice("Ask what she's been feeling, then really listen.", 1, 2),
            Choice("Say 'of course' and change the subject.", 0, -2),
            Choice("Tell her you're busy and end the call.", -1, -2),
        ),
        mood="hurt",
        after=(
            "I keep trying to find us in the quiet. I don't know if you can "
            "hear me anymore."
        ),
    ),
    Scene(
        episode=5,
        title="THE LAST NIGHT",
        question=(
            "Mia meets you beneath the old station clock. Her eyes are wet. "
            "What do you say?"
        ),
        choices=(
            Choice("Tell her you love her, and ask what she needs.", 2, 2),
            Choice("Ask her to stay, but promise nothing will change.", 1, -1),
            Choice("Say nothing. You can't find the words.", -1, -1),
        ),
        mood="hurt",
        after=None,
    ),
)


FINALE_MESSAGES: tuple[str, ...] = (
    (
        "And I'm angry with you. I kept asking you to hear me, and you kept "
        "making me ask. You hurt me, and I'm done."
    ),
    (
        "We're over. I've blocked you. There is no way back together, and I "
        "don't want you to contact me again."
    ),
)


FINALE_SIGNAL = "[ LINK LOST ]  [ SESSION DESYNC ]  [ HEARTBEAT: NO RESPONSE ]"


FINALE_ERRORS: tuple[str, ...] = (
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
)


RELATIONSHIP_STATUS: tuple[str, ...] = (
    "RELATIONSHIP: CLOSED     CHAT: BLOCKED",
    "RECONNECT: DENIED        NEW SEASON: BLOCKED",
    "SEASON 01: END",
)


BLOCKED_MESSAGE = (
    "I'm still angry about how you treated me. We're over, and there is no way "
    "back together. Do not contact me again."
)


def finale_last_words(affection: int, trust: int) -> str:
    """Choose Mia's final opening line using the same thresholds as before."""

    if trust >= 4:
        return "You did listen sometimes. That's what makes this so hard."
    if affection >= 4:
        return "I know there was love here. I just can't live on almost."
    return "I waited for us to feel like us again. I can't wait anymore."


def statistics(choices_made: int, affection: int, trust: int) -> str:
    return (
        f"replies: {choices_made}  ·  affection: {affection:+d}  ·  "
        f"trust: {trust:+d}"
    )
