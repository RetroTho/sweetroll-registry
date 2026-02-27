"""Extended keys extension: enables reporting for modifier + key combinations.

Works in most modern terminal emulators (xterm, gnome-terminal, alacritty,
kitty, wezterm, etc.).  Does not work inside tmux or screen by default.
"""

import curses
import os
import sys

# Escape sequences sent directly to the terminal to toggle "modifyOtherKeys" mode.
_ENABLE = b"\x1b[>4;2m"  # turn extended key reporting on
_DISABLE = b"\x1b[>4;0m"  # restore normal key reporting


def _parse_csi_u(seq):
    """Parse a CSI u-sequence and return a key name string, or None.

    When modifyOtherKeys is active, the terminal encodes key presses as:

        ESC [ <codepoint> ; <modifier> u

    where <codepoint> is the Unicode codepoint of the key and <modifier>
    encodes which modifier keys were held (1 = none, 2 = Shift, 5 = Ctrl,
    6 = Ctrl+Shift, etc.).

    This function converts that into a readable name like "ctrl_shift_z".
    """
    # seq is everything after the ESC, e.g. "[122;6u"
    if not (seq.startswith("[") and seq.endswith("u") and ";" in seq):
        return None

    inner = seq[1:-1]  # strip the leading "[" and trailing "u"
    parts = inner.split(";")
    if len(parts) != 2:
        return None

    try:
        codepoint = int(parts[0])
        modifier = int(parts[1])
    except ValueError:
        return None

    # The modifier value is 1 + (shift bit) + (alt bit × 2) + (ctrl bit × 4)
    bits = modifier - 1
    mods = []
    if bits & 4:
        mods.append("ctrl")
    if bits & 2:
        mods.append("alt")
    if bits & 1:
        mods.append("shift")

    try:
        char = chr(codepoint).lower()
    except (ValueError, OverflowError):
        return None

    # Build a name like "ctrl_shift_z" or just "z" if no modifiers were held
    return "_".join(mods + [char]) if mods else char


def _on_init(event, payload):
    """Enable extended key reporting when the editor starts."""
    os.write(sys.stdout.fileno(), _ENABLE)


def _on_shutdown(event, payload):
    """Restore normal key reporting when the editor exits."""
    os.write(sys.stdout.fileno(), _DISABLE)


def _on_key(event, payload):
    """Intercept ESC and try to read a full extended key sequence."""
    if payload["key"] != 27:  # 27 is the ESC character
        return False

    api = payload["api"]
    win = api.get_win()

    # Switch to non-blocking reads.  Terminal key sequences arrive as a
    # single chunk, so if nothing is waiting immediately this is plain ESC.
    win.nodelay(True)
    chars = []
    while True:
        ch = win.getch()
        if ch == -1:  # no more input right now
            break
        chars.append(ch)
    win.nodelay(False)

    if not chars:
        return False  # plain ESC key — do not consume it

    seq  = "".join(chr(c) for c in chars)
    name = _parse_csi_u(seq)

    if name is None:
        # Not a recognised sequence — push the characters back so nothing
        # is lost and other extensions still see them.
        for ch in reversed(chars):
            curses.ungetch(ch)
        return False

    # Recognised sequence — fire it as a named key event
    api.dispatch_key(name)
    return True  # ESC has been consumed


def setup(register_hook):
    register_hook(0, _on_init, event="init")
    register_hook(0, _on_shutdown, event="shutdown")
    register_hook(0, _on_key, event="key")
