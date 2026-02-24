"""Confirm quit extension: when you have unsaved changes, asks before quitting."""

import curses

PROMPT = "Unsaved changes. Quit anyway? (y/n) "


def _ask_quit(api):
    """Show prompt and wait for y or n. Returns True for yes (allow quit), False for no (cancel quit)."""
    win = api.get_win()
    height, width = api.get_size()
    footer = api.get_footer_rect()
    if footer:
        fy, fx, fh, fw = footer
        y, x, w = fy + fh - 1, fx, fw
    else:
        y, x, w = height - 1, 0, width

    while True:
        try:
            win.move(y, x)
            win.clrtoeol()
            win.addnstr(y, x, PROMPT[: w - 1], w - 1)
            win.refresh()
        except curses.error:
            pass

        key = win.getch()
        if key in (ord("y"), ord("Y")):
            return True
        if key in (ord("n"), ord("N"), 27, curses.KEY_ENTER, 10, 13):
            return False


def _on_before_quit(event, payload):
    api = payload["api"]
    tab_list = api.get_data("tabs.list")
    if tab_list is not None:
        has_unsaved = any(tab["dirty"] for tab in tab_list)
    else:
        has_unsaved = api.is_dirty()
    if not has_unsaved:
        return False  # Nothing to save; allow quit
    if _ask_quit(api):
        return False  # User said yes; allow quit
    api.set_message("Quit cancelled.")
    return True  # User said no; cancel quit


def setup(register_hook):
    register_hook(5, _on_before_quit, event="before_quit")
