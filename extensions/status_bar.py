"""Status bar extension: draws one line at the bottom (filename, dirty, Ln/Col, message)."""

import curses


def _on_layout(event: str, payload: dict) -> None:
    payload["api"].request_footer_rows(1)


def _on_render_overlay(event: str, payload: dict) -> None:
    api = payload["api"]
    win = api.get_win()

    # Build the status text
    path = api.get_path()
    row, col = api.get_cursor()
    filename = path.name if path else "[Untitled]"
    dirty_mark = "*" if api.is_dirty() else "-"
    left = f" {filename} {dirty_mark} | Ln {row + 1}, Col {col + 1} "
    msg = api.get_message().strip()
    text = f"{left}| {msg}" if msg else left

    # Determine where to draw: use footer rect if available, else last row
    footer = api.get_footer_rect()
    if footer:
        fy, fx, fh, fw = footer
        y, x, w = fy + fh - 1, fx, fw
    else:
        height, width = api.get_size()
        y, x, w = height - 1, 0, width

    attr = api.get_data("theme.ui_active", curses.A_REVERSE)
    line = text[:w - 1].ljust(w - 1) if w > 0 else ""
    try:
        win.addnstr(y, x, line, max(0, w - 1), attr)
    except Exception:
        pass


def setup(register_hook):
    register_hook(10, _on_layout, event="layout")
    register_hook(30, _on_render_overlay, event="render_overlay")
