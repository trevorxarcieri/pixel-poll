import utime
from machine import Pin, Signal

# ------------------ Pin assignments ------------------
LEFT_LED = [Signal(Pin(i, Pin.OUT), invert=True) for i in (9, 7, 8)]
RIGHT_LED = [Signal(Pin(i, Pin.OUT), invert=True) for i in (6, 4, 5)]
RED_BTN_LED = Pin(3, Pin.OUT)
GREEN_BTN_LED = Pin(1, Pin.OUT)

RED_BTN = Pin(0, Pin.IN, Pin.PULL_UP)  # active-low
GREEN_BTN = Pin(10, Pin.IN, Pin.PULL_UP)  # active-low
# -----------------------------------------------------


def is_pressed(pin: Pin) -> bool:
    """Return True when an active-low button is physically pressed."""
    return pin.value() == 1


def main() -> None:
    """Main entry point for the IO smoke test."""
    leds = (
        [('LEFT', i, led) for i, led in enumerate(LEFT_LED, start=1)]
        + [('RIGHT', i, led) for i, led in enumerate(RIGHT_LED, start=1)]
        + [('RED_BTN_LED', None, RED_BTN_LED), ('GREEN_BTN_LED', None, GREEN_BTN_LED)]
    )

    for led in LEFT_LED + RIGHT_LED:
        led.off()
    print("Starting IO smoke test… (Ctrl-C to stop)\n")

    while True:
        # Blink LEDs one at a time
        for group, index, led in leds:
            name = f"{group}[{index}]" if index is not None else group
            led.on()
            print(f"{name}: ON")
            utime.sleep(0.5)
            led.off()
            print(f"{name}: OFF")
            utime.sleep(0.5)

            # Poll buttons once per LED cycle
            red_state = is_pressed(RED_BTN)
            green_state = is_pressed(GREEN_BTN)
            print(f"Buttons — RED: {red_state}  GREEN: {green_state}\n")


try:
    main()
except KeyboardInterrupt:
    print("Test stopped.")
