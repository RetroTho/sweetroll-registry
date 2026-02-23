"""Tabs extension: multiple buffers in a tab bar.

Ctrl+K = previous tab
Ctrl+L = next tab
Ctrl+N = new tab
"""

import curses

KEY_PREV_TAB = 11  # Ctrl+K
KEY_NEXT_TAB = 12  # Ctrl+L
KEY_NEW_TAB = 14  # Ctrl+N

tabs = []
current_tab = 0


def make_tab(path=None, lines=None, cursor=(0, 0), scroll_y=0, scroll_x=0, dirty=False):
    """Return a new tab dictionary with the given values (all optional)."""
    return {
        "path": path,
        "lines": lines if lines is not None else [""],
        "cursor": cursor,
        "scroll_y": scroll_y,
        "scroll_x": scroll_x,
        "dirty": dirty,
    }


def save_current_tab(api):
    """Snapshot the editor's current state into the active tab slot."""
    if current_tab >= len(tabs):
        return
    tab = tabs[current_tab]
    tab["path"] = api.get_path()
    tab["lines"] = api.get_lines()
    tab["cursor"] = api.get_cursor()
    tab["scroll_y"] = api.get_scroll_y()
    tab["scroll_x"] = api.get_scroll_x()
    tab["dirty"] = api.is_dirty()


def switch_to_tab(api, index):
    """Restore a tab's saved state into the editor."""
    global current_tab
    if index < 0 or index >= len(tabs):
        return
    current_tab = index
    tab = tabs[index]
    if tab["path"] is not None and not tab["dirty"] and tab["path"].exists():
        api.load_file(tab["path"])
    else:
        api.replace_lines(tab["lines"], dirty=tab["dirty"])
        api.set_path(tab["path"])
    api.set_cursor(tab["cursor"][0], tab["cursor"][1])
    api.set_scroll_y(tab["scroll_y"])
    api.set_scroll_x(tab["scroll_x"])

def _on_init(event, payload):
    """Called once at startup. Turn the initial buffer into the first tab."""
    global tabs, current_tab
    api = payload["api"]
    tabs = [make_tab(
        path = api.get_path(),
        lines = api.get_lines(),
        cursor = api.get_cursor(),
        scroll_y = api.get_scroll_y(),
        scroll_x = api.get_scroll_x(),
        dirty = api.is_dirty(),
    )]
    current_tab = 0


def _on_layout(event, payload):
    """Reserve one row at the top of the screen for the tab bar."""
    payload["api"].request_header_rows(1)


def _on_render_overlay(event, payload):
    """Draw the tab bar across the top of the screen."""
    api = payload["api"]

    # Keep the active tab's dirty flag up to date
    if 0 <= current_tab < len(tabs):
        tabs[current_tab]["dirty"] = api.is_dirty()

    header = api.get_header_rect()
    if not header:
        return

    win = api.get_win()
    hy, hx, hh, hw = header  # row, column, height, width of the header area
    x = hx
    remaining = hw

    for i, tab in enumerate(tabs):
        # Build the label: filename (or "[Untitled]") with "*" when unsaved
        name = tab["path"].name if tab["path"] else "[Untitled]"
        label = name + ("*" if tab["dirty"] else "")

        # Stop drawing if there is no space left
        if remaining <= 1:
            break

        # How many columns does this tab segment get
        seg_len = min(max(4, len(label) + 3), remaining)

        # Pad/trim the text to fit exactly in seg_len columns
        text = (" " + label)[:seg_len - 1].ljust(seg_len - 1)

        # Highlight the active tab; leave others in the normal style
        if i == current_tab:
            attr = api.get_data("theme.ui_active", curses.A_REVERSE)
        else:
            attr = api.get_data("theme.ui", 0)

        try:
            win.addnstr(hy, x, text, seg_len - 1, attr)
        except Exception:
            pass

        x += seg_len
        remaining -= seg_len


def _on_key(event, payload):
    """Handle Ctrl+K / Ctrl+L (switch tab) and Ctrl+N (new tab)."""
    key = payload.get("key")
    api = payload["api"]

    if key == KEY_PREV_TAB:
        save_current_tab(api)
        switch_to_tab(api, (current_tab - 1) % len(tabs))
        return True

    if key == KEY_NEXT_TAB:
        save_current_tab(api)
        switch_to_tab(api, (current_tab + 1) % len(tabs))
        return True

    if key == KEY_NEW_TAB:
        save_current_tab(api)
        tabs.append(make_tab())
        switch_to_tab(api, len(tabs) - 1)
        return True


def _on_saved(event, payload):
    """Mark the active tab as clean after a successful save."""
    if 0 <= current_tab < len(tabs):
        tabs[current_tab]["dirty"] = False


def setup(register_hook):
    register_hook(0, _on_init, event="init")
    register_hook(10, _on_layout, event="layout")
    register_hook(5, _on_key, event="key")
    register_hook(30, _on_render_overlay, event="render_overlay")
    register_hook(0, _on_saved, event="saved")
