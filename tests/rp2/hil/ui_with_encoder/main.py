from encoder.rotary_irq_rp2 import RotaryIRQ
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
                (5, ["Start"], lambda: print("Start selected")),
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
        get_page(
            [(0, ["Right: Yes", "Left: No"], lambda: print("Starting vote"))],
            with_back_button=False,
        ),
    ],
)
router.current_page.display()

encoder = RotaryIRQ(clk_pin="GP2", dt_pin="GP3", pull_up=True)

old_value = encoder.value()


def _encoder_callback():
    global old_value
    new_value = encoder.value()
    if new_value != old_value:
        if new_value > old_value:  # clockwise rotation
            router.current_page.focus_next()
        else:  # counter-clockwise rotation
            router.current_page.focus_previous()
        old_value = new_value
        router.current_page.display()


encoder.add_listener(_encoder_callback)

encoder_button = Pin("GP10", Pin.IN, Pin.PULL_UP)


def _encoder_button_callback(pin: Pin):
    router.current_page.select()
    print("Button pressed")
    router.current_page.display()


encoder_button.irq(trigger=Pin.IRQ_FALLING, handler=_encoder_button_callback)

while True:
    pass
