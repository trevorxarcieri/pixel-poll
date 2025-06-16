import sys

import uselect
from lcd.ili9341 import Display
from machine import SPI, Pin
from ui.core import Router
from ui.widgets import TimeStepperPage, get_page

spi = SPI(
    0,
    baudrate=40_000_000,
    sck=Pin("GP18", Pin.OUT),
    mosi=Pin("GP19", Pin.OUT),
    miso=Pin("GP4", Pin.IN, Pin.PULL_DOWN),
)
display = Display(
    spi, dc=Pin("GP7", Pin.OUT), cs=Pin("GP5", Pin.OUT), rst=Pin("GP6", Pin.OUT)
)

router = Router(
    display,
    [
        get_page(
            [
                (1, ["Settings"], lambda: print("Settings selected")),
                (0, ["Start"], lambda: print("Start selected")),
            ],
            with_back_button=False,
        ),
        get_page([(2, ["Reporting"], None), (3, ["Timing"], None)]),
        get_page(
            [
                (2, ["Anonymous"], lambda: print("Anonymous selected")),
                (2, ["Public"], lambda: print("Public selected")),
            ],
            with_ok_button=True,
            selectable=True,
        ),
        get_page(
            [
                (3, ["Infinite"], lambda: print("Infinite selected")),
                (4, ["Timed"], lambda: print("Timed selected")),
            ],
            with_ok_button=True,
            selectable=True,
        ),
        TimeStepperPage(4, 1, 30),
    ],
)
router.current_page.display()

poll = uselect.poll()
poll.register(sys.stdin, uselect.POLLIN)


def read_key():
    """Return one char if available, else None (non-blocking)."""
    if poll.poll(0):  # ready?
        return sys.stdin.read(1)
    return None


while True:
    ch = read_key()
    if not ch:
        continue

    # Arrow keys arrive as escape sequences: '\x1b', '[', 'A/B/C/D'
    if ch == "\x1b":  # first byte of arrow
        seq = sys.stdin.read(2)  # we already know more bytes are waiting
        if seq in ("[C", "[B"):  # right or down for next
            router.current_page.focus_next()
        elif seq in ("[D", "[A"):  # left or up for prev
            router.current_page.focus_previous()
    elif ch in ("n", "N"):
        router.current_page.focus_next()
    elif ch in ("p", "P"):
        router.current_page.focus_previous()
    elif ch in ("\r", "\n"):  # Enter / Return key
        # Call the select() method on whatever element is currently focused
        router.current_page.select()
    router.current_page.display()
