"""Copy and paste extension: Ctrl+C to copy selected text, Ctrl+V to paste.

Uses the Linux system clipboard via xclip.
Requires the 'selection' extension to be installed for copy to work.
"""

import subprocess

# Key codes for Ctrl+C and Ctrl+V
KEY_COPY = 3
KEY_PASTE = 22


def _get_sorted_range(anchor, cursor):
    """Return (start_row, start_col, end_row, end_col) with start <= end."""
    if anchor <= cursor:
        return anchor[0], anchor[1], cursor[0], cursor[1]
    return cursor[0], cursor[1], anchor[0], anchor[1]


def _extract_selected_text(lines, anchor, cursor):
    """Extract the text between anchor and cursor from the buffer lines."""
    sr, sc, er, ec = _get_sorted_range(anchor, cursor)

    # Single-line selection
    if sr == er:
        return lines[sr][sc:ec]

    # Multi-line selection: first line from start col to end,
    # middle lines in full, last line from start to end col.
    parts = [lines[sr][sc:]]
    for row in range(sr + 1, er):
        parts.append(lines[row])
    parts.append(lines[er][:ec])
    return "\n".join(parts)


def _copy_to_clipboard(text):
    """Send text to the system clipboard using xclip."""
    subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input=text.encode(),
        check=False,
    )


def _read_from_clipboard():
    """Read text from the system clipboard using xclip."""
    result = subprocess.run(
        ["xclip", "-selection", "clipboard", "-o"],
        capture_output=True,
        check=False,
    )
    return result.stdout.decode()


def _on_key(event, payload):
    """Handle Ctrl+C (copy) and Ctrl+V (paste)."""
    api = payload["api"]
    key = payload.get("key")

    if key == KEY_COPY:
        # Read the selection anchor set by the selection extension
        anchor = api.get_data("selection.anchor")
        if anchor is None:
            return False

        cursor = api.get_cursor()
        if anchor == cursor:
            return False

        lines = api.get_lines()
        text = _extract_selected_text(lines, anchor, cursor)
        _copy_to_clipboard(text)
        return True

    if key == KEY_PASTE:
        text = _read_from_clipboard()
        if not text:
            return True

        lines = api.get_lines()
        row, col = api.get_cursor()
        current_line = lines[row]

        # Split the current line at the cursor position
        before = current_line[:col]
        after = current_line[col:]

        # Split pasted text into lines
        pasted_lines = text.split("\n")

        # Build the new lines:
        # - First pasted line joins with text before cursor
        # - Last pasted line joins with text after cursor
        # - Middle pasted lines go in between
        new_lines = lines[:row]
        new_lines.append(before + pasted_lines[0])

        for pasted_line in pasted_lines[1:]:
            new_lines.append(pasted_line)

        # Join the last pasted line with the text after the cursor
        new_lines[-1] = new_lines[-1] + after

        # Add the remaining original lines
        new_lines.extend(lines[row + 1:])

        api.replace_lines(new_lines)

        # Move cursor to end of pasted text
        end_row = row + len(pasted_lines) - 1
        end_col = len(pasted_lines[-1])
        if len(pasted_lines) == 1:
            end_col += col  # Same line, offset by original position
        api.set_cursor(end_row, end_col)

        return True

    return False


def setup(register_hook):
    register_hook(2, _on_key, event="key")
