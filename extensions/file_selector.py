"""File selector extension: open a file from a list in the current directory.

Ctrl+O = open file picker. Use Up/Down to move, Enter to open or go into a folder,
Escape to cancel. Shows ".." to go to the parent directory.
"""

import curses
from pathlib import Path

# Ctrl+O (ASCII 15) opens the file picker
KEY_OPEN = 15


def _get_current_dir(api):
    """Start from the current file's directory, or the process working directory."""
    path = api.get_path()
    if path is not None:
        parent = path.resolve().parent
        if parent.exists():
            return parent
    return Path.cwd()


def _build_entries(current_dir):
    """
    Build a list of (label, path, is_dir) for the picker.
    First entry is ".." to go up, then directories, then files. All sorted by name.
    """
    entries = []

    # ".." to go to parent (only if we're not already at a root)
    if current_dir != current_dir.parent:
        entries.append(("..", current_dir.parent, True))

    try:
        items = list(current_dir.iterdir())
    except OSError:
        return entries

    # Split into directories and files, sort each by name
    dirs = sorted([p for p in items if p.is_dir()], key=lambda p: p.name.lower())
    files = sorted([p for p in items if p.is_file()], key=lambda p: p.name.lower())

    for p in dirs:
        entries.append((p.name + "/", p, True))
    for p in files:
        entries.append((p.name, p, False))

    return entries


def _run_picker(api):
    """
    Show the file list and handle keys until the user opens a file or cancels.
    Opens the chosen file with api.load_file() and returns True, or returns False if cancelled.
    """
    win = api.get_win()
    height, width = api.get_size()

    # Start in the directory of the current file (or cwd)
    current_dir = _get_current_dir(api)
    entries = _build_entries(current_dir)
    selected = 0 if entries else -1

    # How many rows we can use for the list (leave a line for the hint)
    list_height = max(1, height - 1)
    scroll_y = 0  # First visible row in the list

    attr_normal = api.get_data("theme.ui", 0)
    attr_highlight = api.get_data("theme.ui_active", curses.A_REVERSE)

    while True:
        # Keep entries in sync with current_dir
        entries = _build_entries(current_dir)
        if not entries:
            selected = -1
        else:
            selected = min(max(0, selected), len(entries) - 1)

        # Keep selected row visible
        if selected >= 0:
            if selected < scroll_y:
                scroll_y = selected
            if selected >= scroll_y + list_height:
                scroll_y = selected - list_height + 1

        # Draw the list
        win.erase()
        for i in range(list_height):
            idx = scroll_y + i
            if idx >= len(entries):
                break
            label, path, is_dir = entries[idx]
            # Show one line per entry; trim if too long
            display = label[: width - 1].ljust(width - 1) if width > 0 else ""
            attr = attr_highlight if idx == selected else attr_normal
            try:
                win.addnstr(i, 0, display, width - 1, attr)
            except curses.error:
                pass

        # Hint on the last line
        hint = "Enter: open | Up/Down: move | Esc: cancel"
        if width > 0 and height > 0:
            hint_trim = hint[: width - 1]
            try:
                win.addnstr(height - 1, 0, hint_trim, width - 1, attr_normal)
            except curses.error:
                pass

        win.refresh()

        key = win.getch()

        if key == 27:  # Escape
            return False

        if key in (curses.KEY_ENTER, 10, 13):
            if selected < 0 or not entries:
                continue
            _, path, is_dir = entries[selected]
            if is_dir:
                if path == current_dir.parent:
                    current_dir = path
                else:
                    current_dir = path
                selected = 0
                scroll_y = 0
            else:
                api.load_file(path)
                return True

        if key == curses.KEY_UP and selected > 0:
            selected -= 1
        if key == curses.KEY_DOWN and selected < len(entries) - 1:
            selected += 1


def _on_key(event, payload):
    """If the user presses Ctrl+O, run the file picker."""
    if payload.get("key") != KEY_OPEN:
        return False
    api = payload["api"]
    if _run_picker(api):
        api.set_message("Opened file.")
    else:
        api.set_message("Open cancelled.")
    return True  # We handled the key


def setup(register_hook):
    register_hook(5, _on_key, event="key")
