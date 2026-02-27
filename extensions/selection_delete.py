"""Selection delete extension: Backspace deletes all selected text.

Requires the 'selection' extension to be installed.
When text is selected and Backspace is pressed, the entire selection
is removed and the cursor moves to where the selection started.
"""

import curses

# Backspace can be different key codes depending on the terminal
BACKSPACE_KEYS = {curses.KEY_BACKSPACE, 127, 8}


def _get_sorted_range(anchor, cursor):
    """Return (start_row, start_col, end_row, end_col) with start <= end."""
    if anchor <= cursor:
        return anchor[0], anchor[1], cursor[0], cursor[1]
    return cursor[0], cursor[1], anchor[0], anchor[1]


def _on_key(event, payload):
    """If Backspace is pressed while text is selected, delete the selection."""
    api = payload["api"]
    key = payload.get("key")

    # Only handle Backspace
    if key not in BACKSPACE_KEYS:
        return False

    # Check if there is an active selection
    anchor = api.get_data("selection.anchor")
    if anchor is None:
        return False

    cursor = api.get_cursor()
    if anchor == cursor:
        return False

    # Figure out which part of the selection comes first
    sr, sc, er, ec = _get_sorted_range(anchor, cursor)

    lines = api.get_lines()

    # Build new lines: everything before the selection + everything after
    text_before_selection = lines[sr][:sc]
    text_after_selection = lines[er][ec:]
    joined_line = text_before_selection + text_after_selection

    new_lines = lines[:sr] + [joined_line] + lines[er + 1:]

    api.replace_lines(new_lines)
    api.set_cursor(sr, sc)

    # Clear the selection
    api.set_data("selection.anchor", None)

    return True


def setup(register_hook):
    register_hook(1, _on_key, event="key")
