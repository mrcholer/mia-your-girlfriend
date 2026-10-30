# mia-your-girlfriend

Meet Mia, your cute terminal girlfriend. Chat with her, choose your replies, and see where your story goes.

## Start chatting

Requires Python 3.10 or newer.

From the project folder, run:

    python -m pip install -e .
    mia

Or start it directly with:

    python -m mia_your_girlfriend

The first launch opens a polished interactive terminal chat (TUI). On later launches Mia remembers how the season ended.

### Options

    --color        force terminal colors even if NO_COLOR is set
    --no-color     disable terminal colors
    --fast         skip pauses and typing animation
    --classic      use the original line-by-line interface (useful in scripts)
    --version      show the version
    -h, --help     show this help

## Chatting in the TUI

- Type your reply and press **Enter** to send.
- During a choice, press **↑ ↓** to highlight a reply, **Enter** to send, or type the reply number (e.g. `1`) for a quick pick.
- **PgUp / PgDn** scroll the chat; **⇧↑ / ⇧↓** scroll by line.
- **Ctrl+P** toggles the sidebar; **Ctrl+L** redraws the screen.
- **F1** or `?` opens the keys & commands panel; **Esc** closes overlays.
- **Ctrl+C** leaves the chat at any time.

### Commands (type at the prompt)

`/help`  `/status`  `/portrait`  `/portrait legacy`  `/clear`  `/about`  `/quit`

## One-way season

The season has a single finale. Once it ends, Mia blocks this chat permanently — there is no way to start a new season from this installation. That is by design.

## Requirements

No external dependencies. Runs on Linux terminals (and most modern terminals). Colors are disabled automatically when `NO_COLOR` is set or the terminal doesn't support them.
