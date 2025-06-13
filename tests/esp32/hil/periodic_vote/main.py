import time

import neopixel
from ble_vote_controller import BleVoteController
from machine import Pin

PIXEL_PIN = 8  # GPIO your board uses for the NeoPixel
NUM_PIXELS = 1  # there is only one on-board LED

np = neopixel.NeoPixel(Pin(PIXEL_PIN, Pin.OUT), NUM_PIXELS)

on = False


def rx_callback(payload: bytes) -> None:
    """Callback function to handle received messages."""
    print("Received:", payload.decode('utf-8'))
    global on
    if not on:
        np[0] = (50, 0, 0)  # moderate-intensity red  (R,G,B)
        np.write()
        on = True
    else:
        np[0] = (0, 0, 0)  # off
        np.write()
        on = False


voter = BleVoteController(name="ESP32-A", on_rx=rx_callback)

while True:
    voter.send("ACK")  # arbitrary string/bytes
    print("Sent ACK")
    time.sleep(4)  # send every second
