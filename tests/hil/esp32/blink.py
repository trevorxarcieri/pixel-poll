from machine import Pin
import neopixel, time

PIXEL_PIN = 8  # GPIO your board uses for the NeoPixel
NUM_PIXELS = 1  # there is only one on-board LED

np = neopixel.NeoPixel(Pin(PIXEL_PIN, Pin.OUT), NUM_PIXELS)

while True:
    np[0] = (50, 0, 0)  # moderate-intensity red  (R,G,B)
    np.write()
    time.sleep(0.5)
    np[0] = (0, 0, 0)  # off
    np.write()
    time.sleep(0.5)
