"""Syntax highlighting extension: colors keywords, strings, comments, numbers, builtins, and decorators.

Single-line tokenizer — each line is highlighted independently.
Uses theme.syntax_* color roles published by the theme extension.

Known limitation: multi-line strings (triple-quoted) are not fully highlighted.
"""

import curses
import os
import re

# ---------------------------------------------------------------------------
# Language definitions
# ---------------------------------------------------------------------------

LANGUAGES = {
    "python": {
        "extensions": {".py", ".pyw"},
        "patterns": [
            ("comment", re.compile(r"#.*")),
            ("string", re.compile(
                r"[fFbBrRuU]{0,2}"
                r'(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
            )),
            ("decorator", re.compile(r"@\w+")),
            ("keyword", re.compile(
                r"\b(?:False|None|True|and|as|assert|async|await|break|class|continue|"
                r"def|del|elif|else|except|finally|for|from|global|if|import|in|is|"
                r"lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b"
            )),
            ("builtin", re.compile(
                r"\b(?:print|len|range|type|int|str|float|list|dict|set|tuple|bool|"
                r"input|open|enumerate|zip|map|filter|sorted|reversed|abs|max|min|sum|"
                r"any|all|isinstance|hasattr|getattr|setattr|super|property|classmethod|"
                r"staticmethod|self|cls|__init__|__name__|__main__)\b"
            )),
            ("number", re.compile(
                r"\b(?:0[xX][0-9a-fA-F_]+|0[oO][0-7_]+|0[bB][01_]+|"
                r"[0-9][0-9_]*(?:\.[0-9_]*)?(?:[eE][+-]?[0-9_]+)?)\b"
            )),
        ],
    },
}

# Build extension -> language lookup
_EXT_MAP: dict[str, dict] = {}
for _lang in LANGUAGES.values():
    for _ext in _lang["extensions"]:
        _EXT_MAP[_ext] = _lang

# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def _tokenize_line(line, lang):
    """Walk left-to-right; first pattern match at each position wins.

    Returns [(token_type, start_col, end_col), ...].
    """
    patterns = lang["patterns"]
    tokens = []
    pos = 0
    length = len(line)

    while pos < length:
        matched = False
        for token_type, regex in patterns:
            m = regex.match(line, pos)
            if m:
                start, end = m.span()
                tokens.append((token_type, start, end))
                pos = end
                matched = True
                break
        if not matched:
            pos += 1

    return tokens

# ---------------------------------------------------------------------------
# Hook functions
# ---------------------------------------------------------------------------

# Cached state to avoid re-detecting language every render
_cached_path: str | None = None
_cached_lang: dict | None = None

# Default attrs in case theme isn't loaded yet
_DEFAULT_ATTR = curses.A_NORMAL


def _on_render_overlay(event, payload):
    global _cached_path, _cached_lang

    api = payload["api"]

    # Detect language from file path (re-detect on path change)
    path = api.get_path()
    if path != _cached_path:
        _cached_path = path
        if path:
            ext = os.path.splitext(path)[1]
            _cached_lang = _EXT_MAP.get(ext)
        else:
            _cached_lang = None

    if _cached_lang is None:
        return

    # Load theme colors
    colors = {
        "keyword": api.get_data("theme.syntax_keyword", _DEFAULT_ATTR),
        "string": api.get_data("theme.syntax_string", _DEFAULT_ATTR),
        "comment": api.get_data("theme.syntax_comment", _DEFAULT_ATTR),
        "number": api.get_data("theme.syntax_number", _DEFAULT_ATTR),
        "builtin": api.get_data("theme.syntax_builtin", _DEFAULT_ATTR),
        "decorator": api.get_data("theme.syntax_decorator", _DEFAULT_ATTR),
    }

    rect = api.get_content_rect()
    if not rect:
        return

    cy, cx, ch, cw = rect
    scroll_y = api.get_scroll_y()
    scroll_x = api.get_scroll_x()
    win = api.get_win()
    lines = api.get_lines()

    for screen_row in range(ch):
        line_idx = scroll_y + screen_row
        if line_idx >= len(lines):
            break

        line = lines[line_idx]
        if not line:
            continue

        tokens = _tokenize_line(line, _cached_lang)

        for token_type, start, end in tokens:
            attr = colors.get(token_type)
            if attr is None:
                continue

            # Clamp to visible portion
            vis_start = max(start, scroll_x)
            vis_end = min(end, scroll_x + cw)

            if vis_start >= vis_end:
                continue

            text = line[vis_start:vis_end]
            screen_x = cx + (vis_start - scroll_x)

            try:
                win.addnstr(cy + screen_row, screen_x, text, vis_end - vis_start, attr)
            except curses.error:
                pass


def setup(register_hook):
    register_hook(20, _on_render_overlay, event="render_overlay")
