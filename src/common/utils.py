"""Common utilities used across both the central and peripheral modules."""

from typing import Any, Callable

import micropython
import utime
from machine import Pin


def get_db_button_irq(
    callback: Callable, pin: Pin, arg: Any, debounce_ms: int
) -> Callable[[Pin], None]:
    """Get a debounced IRQ handler for `pin`."""
    last_time = 0  # captured in closure

    def irq_handler(_: Pin) -> None:
        nonlocal last_time
        now = utime.ticks_ms()
        if utime.ticks_diff(now, last_time) < debounce_ms:
            return
        last_time = now
        micropython.schedule(callback, arg)

    return irq_handler
