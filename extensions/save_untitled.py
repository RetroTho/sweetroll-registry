"""Save untitled files extension: on Ctrl+S with no path, prompt for filename then let core save."""

import curses

PROMPT_PREFIX = "Save as: "
MAX_PATH_LEN = 512


def _prompt_filename(api):
    """Show a line prompt for filename. Returns the path string or None if cancelled."""
    win = api.get_win()
    height, width = api.get_size()
    footer = api.get_footer_rect()
    if footer:
        fy, fx, fh, fw = footer
        y, x = fy + fh - 1, fx
        w = fw
    else:
        y, x = height - 1, 0
        w = width

    if w <= len(PROMPT_PREFIX) + 1:
        return None

    name = ""

    while True:
        line = PROMPT_PREFIX + name
        visible = line[-(w - 1) :] if len(line) > w - 1 else line
        try:
            win.move(y, x)
            win.clrtoeol()
            win.addnstr(y, x, visible, w - 1)
            win.refresh()
        except curses.error:
            pass

        key = win.getch()
        if key in (curses.KEY_ENTER, 10, 13):
            return name.strip() or None
        if key == 27:  # Escape
            return None
        if key in (curses.KEY_BACKSPACE, 127):
            name = name[:-1]
        elif 32 <= key <= 126 and len(name) < MAX_PATH_LEN:
            name += chr(key)


def _on_before_save(event, payload):
    api = payload["api"]
    if api.get_path() is not None:
        return False  # Core will save as usual

    path_str = _prompt_filename(api)
    if path_str is None:
        api.set_message("Save cancelled.")
        return True  # Handled; do not call buffer.save()
    api.set_path(path_str)
    return False  # Core will perform buffer.save()


def setup(register_hook):
    register_hook(0, _on_before_save, event="before_save")
