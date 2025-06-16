from lcd.ili9341 import Display
from machine import SPI, Pin
from ui.core import Router
from ui.widgets import get_page
from utime import ticks_diff, ticks_ms

spi = SPI(
    0,
    baudrate=40000000,
    sck=Pin("GP18", Pin.OUT),
    mosi=Pin("GP19", Pin.OUT),
    miso=Pin("GP4", Pin.IN, Pin.PULL_DOWN),
)
display = Display(
    spi, dc=Pin("GP7", Pin.OUT), cs=Pin("GP5", Pin.OUT), rst=Pin("GP6", Pin.OUT)
)
# card = Card(1, 0, 0, 200, 200, ["Hello", "World!"])
# page = Page([BackButton(), card])
waiting_text = ["Waiting"]
page = get_page(
    [(1, ["Hello", "World!"], None), (0, waiting_text, None)], with_back_button=True
)
router = Router(display, [page])
router.current_page.display()

timer = ticks_ms()
cur_ms = 0
while True:
    cur_ms += ticks_diff(ticks_ms(), timer)
    timer = ticks_ms()
    if cur_ms > 1000:
        cur_ms = 0
        router.current_page.focus = (router.current_page.focus + 1) % (
            len(router.current_page.elements) + 1
        )
        waiting_text[0] += "."
        if len(waiting_text[0]) > 10:
            waiting_text[0] = waiting_text[0][:-4]
        router.current_page.display()
