"""Tabs extension: multiple buffers in a tab bar; Ctrl+K/Ctrl+L switch, Ctrl+N new tab."""

from dataclasses import dataclass
from pathlib import Path

import curses

# Ctrl+K prev, Ctrl+L next, Ctrl+N new tab (ASCII control codes)
KEY_PREV_TAB = 11   # Ctrl+K
KEY_NEXT_TAB = 12   # Ctrl+L
KEY_NEW_TAB = 14    # Ctrl+N


@dataclass
class TabState:
    path: Path | None
    lines: list[str]
    cursor: tuple[int, int]
    scroll_y: int
    scroll_x: int
    dirty: bool


_tabs: list[TabState] = []
_current: int = 0


def _persist_current(api) -> None:
    """Write current buffer into _tabs[_current]."""
    if _current >= len(_tabs):
        return
    t = _tabs[_current]
    t.path = api.get_path()
    t.lines = api.get_lines()
    t.cursor = api.get_cursor()
    t.scroll_y = api.get_scroll_y()
    t.scroll_x = api.get_scroll_x()
    t.dirty = api.is_dirty()


def _activate_tab(api, index: int) -> None:
    """Switch to tab at index, updating _current and restoring its buffer state."""
    global _current
    if index < 0 or index >= len(_tabs):
        return
    _current = index
    t = _tabs[index]
    if t.path is not None and not t.dirty:
        api.load_file(t.path)
    else:
        api.replace_lines(t.lines, dirty=t.dirty)
        api.set_path(t.path)
    api.set_cursor(t.cursor[0], t.cursor[1])
    api.set_scroll_y(t.scroll_y)
    api.set_scroll_x(t.scroll_x)


def _on_init(event: str, payload: dict) -> None:
    api = payload["api"]
    global _tabs, _current
    _tabs = [
        TabState(
            path=api.get_path(),
            lines=api.get_lines(),
            cursor=api.get_cursor(),
            scroll_y=api.get_scroll_y(),
            scroll_x=api.get_scroll_x(),
            dirty=api.is_dirty(),
        )
    ]
    _current = 0


def _on_layout(event: str, payload: dict) -> None:
    payload["api"].request_header_rows(1)


def _on_render_overlay(event: str, payload: dict) -> None:
    api = payload["api"]
    if 0 <= _current < len(_tabs):
        _tabs[_current].dirty = api.is_dirty()
    header = api.get_header_rect()
    if not header:
        return
    win = api.get_win()
    hy, hx, hh, hw = header
    x = hx
    remaining = hw
    for i, t in enumerate(_tabs):
        label = (t.path.name if t.path else "[Untitled]") + ("*" if t.dirty else "")
        # Each tab takes at least 4 columns, capped by remaining space
        if remaining > 1:
            seg_len = min(max(4, len(label) + 3), remaining)
        else:
            seg_len = 0
        if seg_len == 0:
            break
        text = (" " + label)[:seg_len - 1].ljust(seg_len - 1)
        attr = api.get_data("theme.ui_active", curses.A_REVERSE) if i == _current else api.get_data("theme.ui", 0)
        try:
            win.addnstr(hy, x, text, seg_len - 1, attr)
        except Exception:
            pass
        x += seg_len
        remaining -= seg_len


def _on_key(event: str, payload: dict) -> bool | None:
    key = payload.get("key")
    api = payload["api"]
    if key == KEY_PREV_TAB:
        _persist_current(api)
        _activate_tab(api, (_current - 1) % len(_tabs))
        return True
    if key == KEY_NEXT_TAB:
        _persist_current(api)
        _activate_tab(api, (_current + 1) % len(_tabs))
        return True
    if key == KEY_NEW_TAB:
        _persist_current(api)
        _tabs.append(TabState(path=None, lines=[""], cursor=(0, 0), scroll_y=0, scroll_x=0, dirty=False))
        _activate_tab(api, len(_tabs) - 1)
        return True


def _on_saved(event: str, payload: dict) -> None:
    if 0 <= _current < len(_tabs):
        _tabs[_current].dirty = False


def setup(register_hook):
    register_hook(0, _on_init, event="init")
    register_hook(10, _on_layout, event="layout")
    register_hook(5, _on_key, event="key")   # 5 runs before the editor's default key handling
    register_hook(30, _on_render_overlay, event="render_overlay")
    register_hook(0, _on_saved, event="saved")
