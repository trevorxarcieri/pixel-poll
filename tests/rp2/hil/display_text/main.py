from lcd.ili9341 import Display, color565
from lcd.xglcd_font import XglcdFont
from machine import SPI, Pin
from utime import (
    ticks_diff,  # type: ignore[reportAttributeAccessIssue]
    ticks_ms,  # type: ignore[reportAttributeAccessIssue]
)

# Baud rate of 40000000 seems about the max
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
font = XglcdFont("Robotron13x21.c", 13, 21)

try:
    display.clear()

    colors = [
        color565(255, 0, 0),
        color565(0, 255, 0),
        color565(0, 0, 255),
        color565(255, 255, 0),
        color565(0, 255, 255),
        color565(255, 0, 255),
    ]

    i = 0
    timer = ticks_ms()
    while True:
        display.draw_text(
            0, display.height, 'HELLO WORLD!', font, colors[i], landscape=True
        )
        # Attempt to set framerate to 30 FPS
        timer_dif = 1000 - ticks_diff(ticks_ms(), timer)
        if timer_dif < 0:
            i = (i + 1) % len(colors)
            timer = ticks_ms()

except KeyboardInterrupt:
    display.cleanup()
