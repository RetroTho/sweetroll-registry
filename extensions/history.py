"""History extension: keeps a list of past buffer states.

Stores history.states (list of {lines, cursor}) and history.current (latest state).
Other extensions can use these.
"""

MAX_HISTORY = 100


def _make_state(api):
    """Capture the current buffer contents and cursor position."""
    return {
        "lines": api.get_lines(),
        "cursor": api.get_cursor(),
    }


def _on_init(event, payload):
    """Store initial state."""
    api = payload["api"]
    api.set_data("history.states", [])
    api.set_data("history.current", _make_state(api))


def _on_before_render(event, payload):
    """Append to history when the buffer text changes (cursor-only moves do not)."""
    api = payload["api"]
    states = list(api.get_data("history.states", []))
    current = api.get_data("history.current")
    new_state = _make_state(api)

    if current is None:
        api.set_data("history.current", new_state)
        return

    if new_state["lines"] == current["lines"]:
        api.set_data("history.current", new_state)
        return

    states.append(current)
    if len(states) > MAX_HISTORY:
        states = states[-MAX_HISTORY:]
    api.set_data("history.states", states)
    api.set_data("history.current", new_state)


def setup(register_hook):
    register_hook(0, _on_init, event="init")
    register_hook(20, _on_before_render, event="before_render")
