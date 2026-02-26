"""Text selection extension: Shift+Arrow to select, highlighted with A_REVERSE.

Selection is defined by an anchor point and the current cursor position.
Any non-shift key clears the selection.
"""

import curses

# Shift+Arrow key codes (curses constants / common terminal values)
KEY_SLEFT = 393
KEY_SRIGHT = 402
KEY_SUP = 337
KEY_SDOWN = 336

_SHIFT_KEYS = {KEY_SLEFT, KEY_SRIGHT, KEY_SUP, KEY_SDOWN}

# Module-level selection state
_anchor: tuple[int, int] | None = None


def _get_sorted_range(anchor: tuple[int, int], cursor: tuple[int, int]):
    """Return (start_row, start_col, end_row, end_col) with start <= end."""
    if anchor <= cursor:
        return anchor[0], anchor[1], cursor[0], cursor[1]
    return cursor[0], cursor[1], anchor[0], anchor[1]


def _on_key(event, payload):
    """Handle shift+arrow keys for selection; clear on anything else."""
    global _anchor
    api = payload["api"]
    key = payload.get("key")

    if key not in _SHIFT_KEYS:
        # Any non-shift key clears the selection
        if _anchor is not None:
            _anchor = None
            api.set_data("selection.anchor", None)
        return False  # Let core handle

    # Start selection at current cursor if not already active
    if _anchor is None:
        _anchor = api.get_cursor()
        api.set_data("selection.anchor", _anchor)

    # Move the cursor (mirrors core arrow-key logic)
    row, col = api.get_cursor()
    lines = api.get_lines()

    if key == KEY_SLEFT:
        if col > 0:
            api.set_cursor(row, col - 1)
    elif key == KEY_SRIGHT:
        if col < len(lines[row]):
            api.set_cursor(row, col + 1)
    elif key == KEY_SUP:
        if row > 0:
            api.set_cursor(row - 1, col)
    elif key == KEY_SDOWN:
        if row < len(lines) - 1:
            api.set_cursor(row + 1, col)

    return True  # Consume the key so core doesn't also move


def _on_render_overlay(event, payload):
    """Overdraw selected characters with highlight attribute."""
    if _anchor is None:
        return

    api = payload["api"]
    cursor = api.get_cursor()

    if _anchor == cursor:
        return  # Nothing to highlight

    rect = api.get_content_rect()
    if not rect:
        return

    cy, cx, ch, cw = rect
    scroll_y = api.get_scroll_y()
    scroll_x = api.get_scroll_x()
    win = api.get_win()
    lines = api.get_lines()

    sr, sc, er, ec = _get_sorted_range(_anchor, cursor)

    for screen_row in range(ch):
        line_idx = scroll_y + screen_row
        if line_idx < sr or line_idx > er:
            continue
        if line_idx >= len(lines):
            break

        line = lines[line_idx]

        # Determine selection columns for this line
        if line_idx == sr:
            sel_start = sc
        else:
            sel_start = 0

        if line_idx == er:
            sel_end = ec
        else:
            sel_end = len(line)

        # Clamp to visible portion
        vis_start = max(sel_start, scroll_x)
        vis_end = min(sel_end, scroll_x + cw)

        if vis_start >= vis_end:
            continue

        text = line[vis_start:vis_end]
        screen_x = cx + (vis_start - scroll_x)

        try:
            win.addnstr(cy + screen_row, screen_x, text, vis_end - vis_start, curses.A_REVERSE)
        except curses.error:
            pass


def setup(register_hook):
    register_hook(3, _on_key, event="key")
    register_hook(25, _on_render_overlay, event="render_overlay")
