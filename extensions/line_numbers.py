"""Line numbers extension: shows a column of line numbers to the left of the text.

Uses the left sidebar area. Numbers are 1-based and right-aligned.
"""

import curses

# How many columns to reserve for the line number column (5 fits up to 99999)
GUTTER_WIDTH = 5


def _on_layout(event, payload):
    """Ask the editor to reserve space on the left for line numbers."""
    payload["api"].request_left_columns(GUTTER_WIDTH)


def _on_render_overlay(event, payload):
    """Draw one line number per visible row in the left gutter."""
    api = payload["api"]
    left = api.get_left_rect()
    if not left:
        return

    ly, lx, lh, lw = left
    scroll_y = api.get_scroll_y()
    num_lines = len(api.get_lines())
    cursor_row = api.get_cursor()[0]

    # Use a dim style for the gutter; highlight the current line's number if desired
    attr_dim = api.get_data("theme.ui", curses.A_DIM)
    attr_current = api.get_data("theme.ui_active", curses.A_REVERSE)
    win = api.get_win()

    for row in range(lh):
        line_idx = scroll_y + row
        if line_idx >= num_lines:
            break
        line_num = line_idx + 1
        text = str(line_num).rjust(lw)  # right-align: spaces on left for short numbers; 12345 fills all 5
        if len(text) > lw:
            text = text[-lw:]
        use_attr = attr_current if line_idx == cursor_row else attr_dim
        try:
            win.addnstr(ly + row, lx, text, max(0, lw), use_attr)
        except curses.error:
            pass


def setup(register_hook):
    register_hook(10, _on_layout, event="layout")
    register_hook(30, _on_render_overlay, event="render_overlay")
