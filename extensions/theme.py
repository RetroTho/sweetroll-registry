"""Theme extension: publishes semantic color roles to the shared data store.

Roles set:
  theme.text       — main editor text (used for win.bkgd)
  theme.ui         — inactive UI elements (e.g. inactive tabs)
  theme.ui_active  — active/selected UI elements (e.g. active tab, status bar)

Extensions read these with api.get_data("theme.<role>", <fallback>).
"""

import curses


def _on_init(event, payload):
    api = payload["api"]
    api.set_data("theme.text", api.color_pair(-1, -1))
    api.set_data("theme.ui", api.color_pair(curses.COLOR_WHITE, curses.COLOR_BLACK))
    api.set_data("theme.ui_active", api.color_pair(curses.COLOR_BLACK, curses.COLOR_WHITE))


def _on_before_render(event, payload):
    api = payload["api"]
    text_attr = api.get_data("theme.text")
    if text_attr is not None:
        api.get_win().bkgd(" ", text_attr)


def setup(register_hook):
    register_hook(0, _on_init, event="init")
    register_hook(5, _on_before_render, event="before_render")
