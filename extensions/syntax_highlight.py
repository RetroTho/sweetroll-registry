"""Syntax highlighting extension: colors keywords, strings, comments, numbers, builtins, and decorators.

Stateful tokenizer — tracks multi-line constructs (triple-quoted strings, block
comments) across line boundaries.
Uses theme.syntax_* color roles published by the theme extension.
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
                r'(?:"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
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
        "multiline": [
            ("string", re.compile(r'[fFbBrRuU]{0,2}"""'), re.compile(r'"""')),
            ("string", re.compile(r"[fFbBrRuU]{0,2}'''"), re.compile(r"'''")),
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

def _tokenize_buffer(lines, lang):
    """Tokenize all lines with multi-line state tracking.

    Returns a list of token lists, one per line.
    Each token is (token_type, start_col, end_col).
    """
    patterns = lang["patterns"]
    multiline = lang.get("multiline", [])
    all_tokens = []

    # Multi-line state: None, or (token_type, close_regex)
    ml_state = None

    for line in lines:
        tokens = []
        pos = 0
        length = len(line)

        # If we're inside a multi-line construct from a previous line,
        # search for the closing delimiter.
        if ml_state is not None:
            token_type, close_re = ml_state
            m = close_re.search(line)
            if m:
                tokens.append((token_type, 0, m.end()))
                pos = m.end()
                ml_state = None
            else:
                tokens.append((token_type, 0, length))
                all_tokens.append(tokens)
                continue

        while pos < length:
            # Try multi-line openers first
            ml_matched = False
            for token_type, open_re, close_re in multiline:
                m = open_re.match(line, pos)
                if m:
                    # Check if closer exists on the same line after the opener
                    close_m = close_re.search(line, m.end())
                    if close_m:
                        tokens.append((token_type, m.start(), close_m.end()))
                        pos = close_m.end()
                    else:
                        tokens.append((token_type, m.start(), length))
                        ml_state = (token_type, close_re)
                        pos = length
                    ml_matched = True
                    break

            if ml_matched:
                continue

            # Try single-line patterns
            matched = False
            for token_type, regex in patterns:
                m = regex.match(line, pos)
                if m:
                    tokens.append((token_type, m.start(), m.end()))
                    pos = m.end()
                    matched = True
                    break

            if not matched:
                pos += 1

        all_tokens.append(tokens)

    return all_tokens

# ---------------------------------------------------------------------------
# Hook functions
# ---------------------------------------------------------------------------

# Cached state
_cached_path: str | None = None
_cached_lang: dict | None = None
_cached_lines: list[str] | None = None
_cached_tokens: list[list[tuple]] | None = None

# Default attrs in case theme isn't loaded yet
_DEFAULT_ATTR = curses.A_NORMAL


def _on_render_overlay(event, payload):
    global _cached_path, _cached_lang, _cached_lines, _cached_tokens

    api = payload["api"]

    # Detect language from file path (re-detect on path change)
    path = api.get_path()
    if path != _cached_path:
        _cached_path = path
        _cached_lines = None
        if path:
            ext = os.path.splitext(path)[1]
            _cached_lang = _EXT_MAP.get(ext)
        else:
            _cached_lang = None

    if _cached_lang is None:
        return

    # Re-tokenize only when buffer content changes
    lines = api.get_lines()
    if lines != _cached_lines:
        _cached_lines = lines
        _cached_tokens = _tokenize_buffer(lines, _cached_lang)

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

    for screen_row in range(ch):
        line_idx = scroll_y + screen_row
        if line_idx >= len(_cached_tokens):
            break

        tokens = _cached_tokens[line_idx]
        if not tokens:
            continue

        line = _cached_lines[line_idx]

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
