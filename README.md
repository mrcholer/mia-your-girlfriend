# mia-your-girlfriend

A choice-driven terminal chat story starring Mia. Reply through five scenes, watch the relationship fall apart, and reach a one-way season finale with an angry breakup, a blocked-chat screen, and a cascading error log.

Mia's terminal portrait is an original symbol illustration with pale hair, a dark bow, blue eyes, and heart accessories.

## Run from the source folder

Requires Python 3.10 or newer. No runtime packages are needed.

Run with: python .\season.py --color

Choose a reply by entering its number. Use --fast to skip pauses or --no-color to disable ANSI colors.

## Install the command

From the project folder, run:

    python -m pip install -e .
    mia-your-girlfriend --color

You can also run the package with python -m mia_your_girlfriend --color.

## Permanent block

After Season 01 ends, the game saves a closed-state marker in the current Windows user's Local AppData. Future launches refuse to start another season, even after moving or reinstalling the project. The marker is intentionally excluded from Git so each new user can play the story once.
