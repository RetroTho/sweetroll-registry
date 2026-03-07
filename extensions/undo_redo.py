"""Undo/redo extension: Ctrl+Z to undo, Ctrl+Shift+Z to redo.

Uses history.states and history.current from the history extension; keeps its own
redo stack (undo_redo.redo_stack). Depends on extended_keys and history.

Accepts both string names from extended_keys ("ctrl_z", "ctrl_shift_z") and the
raw ASCII code 26 for Ctrl+Z, since many terminals send 26 instead of the CSI u
sequence (e.g. for job control or when modifyOtherKeys isn't used for that key).
"""

MAX_HISTORY = 100  # cap when pushing current onto history on redo

KEY_CTRL_Z = 26  # Ctrl+Z
KEY_CTRL_SHIFT_Z = "ctrl_shift_z"  # Ctrl+Shift+Z


def _restore_state(api, state):
    """Replace the buffer with `state` and move the cursor."""
    if not state:
        return
    api.replace_lines(state.get("lines", []), dirty=True)
    row, col = state.get("cursor", (0, 0))
    api.set_cursor(row, col)


def _on_key(event, payload):
    """Handle Ctrl+Z (undo) and Ctrl+Shift+Z (redo) key events."""
    api = payload["api"]
    key = payload["key"]

    if key == KEY_CTRL_Z:
        states = list(api.get_data("history.states", []))
        current = api.get_data("history.current")
        if not states or current is None:
            return False

        previous = states.pop()
        redo_stack = list(api.get_data("undo_redo.redo_stack", []))
        redo_stack.append(current)
        api.set_data("history.states", states)
        api.set_data("history.current", previous)
        api.set_data("undo_redo.redo_stack", redo_stack)
        _restore_state(api, previous)
        return True

    if key == KEY_CTRL_SHIFT_Z:
        redo_stack = list(api.get_data("undo_redo.redo_stack", []))
        if not redo_stack:
            return False

        current = api.get_data("history.current")
        next_state = redo_stack.pop()
        api.set_data("undo_redo.redo_stack", redo_stack)
        if current is not None:
            states = list(api.get_data("history.states", []))
            states.append(current)
            if len(states) > MAX_HISTORY:
                states = states[-MAX_HISTORY:]
            api.set_data("history.states", states)
        api.set_data("history.current", next_state)
        _restore_state(api, next_state)
        return True

    return False


def setup(register_hook):
    register_hook(0, _on_key, event="key")

