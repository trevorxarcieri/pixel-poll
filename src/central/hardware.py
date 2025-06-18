"""Hardware abstraction layer for the central module."""

import micropython
from encoder.rotary_irq_rp2 import RotaryIRQ
from lcd.ili9341 import Display
from machine import SPI, Pin
from ui.core import Router


def init_display() -> Display:
    """Initialize the display for the central module."""
    return Display(
        SPI(
            0,
            baudrate=40_000_000,
            sck=Pin("GP18", Pin.OUT),
            mosi=Pin("GP19", Pin.OUT),
            miso=Pin("GP4", Pin.IN, Pin.PULL_UP),
        ),
        dc=Pin("GP7", Pin.OUT),
        cs=Pin("GP5", Pin.OUT),
        rst=Pin("GP6", Pin.OUT),
    )


def init_encoder() -> tuple[RotaryIRQ, Pin]:
    """Initialize the rotary encoder for the central module."""
    enc = RotaryIRQ(clk_pin="GP2", dt_pin="GP3", pull_up=True)
    btn = Pin("GP10", Pin.IN, Pin.PULL_UP)
    return enc, btn


def attach_encoder_navigation(enc: RotaryIRQ, router: Router) -> None:
    """Register a movement listener that scrolls the Router's focus."""
    old_val = enc.value()  # local, captured by the IRQ closure

    def _irq() -> None:
        nonlocal old_val
        diff = enc.value() - old_val
        if diff:  # ignore zero
            old_val += diff
            micropython.schedule(_handle, diff)

    def _handle(delta: int) -> None:
        if delta > 0:
            router.current_page.focus_next()
        elif delta < 0:
            router.current_page.focus_previous()
        router.current_page.display()

    enc.add_listener(_irq)
