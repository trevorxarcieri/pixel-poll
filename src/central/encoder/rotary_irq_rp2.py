"""Proveides RotaryIRQ class for Raspberry Pi Pico.

Adapted from https://github.com/miketeachman/micropython-rotary.

MIT License (MIT)
Copyright (c) 2020 Mike Teachman
Copyright (c) 2021 Eric Moyer
https://opensource.org/licenses/MIT

Platform-specific MicroPython code for the rotary encoder module
Raspberry Pi Pico implementation

Documentation:
https://github.com/MikeTeachman/micropython-rotary
"""

from typing import Any

from encoder.rotary import Rotary
from machine import Pin

IRQ_RISING_FALLING = Pin.IRQ_RISING | Pin.IRQ_FALLING


class RotaryIRQ(Rotary):
    """RotaryIRQ class for Raspberry Pi Pico."""

    def __init__(
        self,
        *,
        clk_pin: Any,
        dt_pin: Any,
        min_val: int = 0,
        max_val: int = 10,
        incr: int = 1,
        reverse: bool = False,
        range_mode: int = Rotary.RANGE_UNBOUNDED,
        pull_up: bool = False,
        half_step: bool = False,
        invert: bool = False,
    ):
        """Initialize the RotaryIRQ."""
        super().__init__(min_val, max_val, incr, reverse, range_mode, half_step, invert)

        if pull_up:
            self._pin_clk = Pin(clk_pin, Pin.IN, Pin.PULL_UP)
            self._pin_dt = Pin(dt_pin, Pin.IN, Pin.PULL_UP)
        else:
            self._pin_clk = Pin(clk_pin, Pin.IN)
            self._pin_dt = Pin(dt_pin, Pin.IN)

        self._hal_enable_irq()

    def _enable_clk_irq(self) -> None:
        self._pin_clk.irq(self._process_rotary_pins, IRQ_RISING_FALLING)

    def _enable_dt_irq(self) -> None:
        self._pin_dt.irq(self._process_rotary_pins, IRQ_RISING_FALLING)

    def _disable_clk_irq(self) -> None:
        self._pin_clk.irq(None, 0)

    def _disable_dt_irq(self) -> None:
        self._pin_dt.irq(None, 0)

    def _hal_get_clk_value(self) -> int:
        return self._pin_clk.value()

    def _hal_get_dt_value(self) -> int:
        return self._pin_dt.value()

    def _hal_enable_irq(self) -> None:
        self._enable_clk_irq()
        self._enable_dt_irq()

    def _hal_disable_irq(self) -> None:
        self._disable_clk_irq()
        self._disable_dt_irq()

    def _hal_close(self) -> None:
        self._hal_disable_irq()
