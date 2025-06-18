"""Constants for the central module."""

from micropython import const


class ReportingMode:
    """Enum-like class for reporting modes."""

    PUBLIC = "Public"
    ANONYMOUS = "Anonymous"


class TimingMode:
    """Enum-like class for timing modes."""

    INFINITE = "Infinite"
    TIMED = "Timed"


ELLIPSIS = "..."
BTN_DEBOUNCE_MS = const(400)
