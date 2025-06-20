"""Main entry point for the controller module."""

import micropython
import uasyncio
from ble_vote_controller import BleVoteController
from lib.consts import VoteCommand, VoteInfo
from lib.threadsafe_queue import ThreadSafeQueue
from lib.utils import get_db_button_irq
from machine import Pin, Signal

# Allocate buffer for hard-crash tracebacks inside IRQ
micropython.alloc_emergency_exception_buf(100)

# --------------------------------------------------------------------
# GPIO setup
# --------------------------------------------------------------------
LEFT_LED = [Signal(Pin(i, Pin.OUT), invert=True) for i in (9, 7, 8)]
RIGHT_LED = [Signal(Pin(i, Pin.OUT), invert=True) for i in (6, 4, 5)]
RED_BTN_LED = Pin(3, Pin.OUT)
GREEN_BTN_LED = Pin(1, Pin.OUT)

RED_BTN = Pin(0, Pin.IN, Pin.PULL_UP)  # active-low
GREEN_BTN = Pin(10, Pin.IN, Pin.PULL_UP)


queue: ThreadSafeQueue  # forward declaration; filled in main()
voter: BleVoteController | None = None  # set in main()
_DEBOUNCE_MS = micropython.const(40)  # mechanical bounce time


async def consume_queue(q: ThreadSafeQueue) -> None:
    """Consume commands from the queue and update LEDs accordingly."""
    while True:
        payload = await q.get()  # await - no busy polling
        if payload == VoteCommand.START:
            RED_BTN_LED.on()
            GREEN_BTN_LED.on()
        elif payload == VoteCommand.STOP:
            RED_BTN_LED.off()
            GREEN_BTN_LED.off()
        elif payload == VoteCommand.INDICATE_YES:
            RIGHT_LED[0].off()
            RIGHT_LED[1].on()
            RIGHT_LED[2].off()
        elif payload == VoteCommand.INDICATE_NO:
            LEFT_LED[0].on()
            LEFT_LED[1].off()
            LEFT_LED[2].off()
        elif payload == VoteCommand.INDICATE_NONE:
            LEFT_LED[0].off()
            LEFT_LED[1].off()
            LEFT_LED[2].off()
            RIGHT_LED[0].off()
            RIGHT_LED[1].off()
            RIGHT_LED[2].off()


def _scheduled_send(vote: bytes) -> None:
    """Runs outside ISR. Sends BLE vote and resets LEDs."""
    global voter
    if voter:
        voter.send(vote)
        print(f"Sent vote: {"yes" if vote == VoteInfo.YES else "no"}")
    RED_BTN_LED.off()
    GREEN_BTN_LED.off()


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> None:
    """Main entry point for the controller application."""
    global queue, voter
    # Turn off left/right LEDs
    for pin in LEFT_LED + RIGHT_LED:
        pin.off()

    queue = ThreadSafeQueue(16)

    voter = BleVoteController(
        name="PP Ctrl",
        on_rx=lambda payload: queue.put_sync(payload),
    )

    # Hook IRQs - falling edge for active-low buttons
    RED_BTN.irq(
        trigger=Pin.IRQ_FALLING,
        handler=get_db_button_irq(_scheduled_send, RED_BTN, VoteInfo.NO, _DEBOUNCE_MS),
    )
    GREEN_BTN.irq(
        trigger=Pin.IRQ_FALLING,
        handler=get_db_button_irq(
            _scheduled_send, GREEN_BTN, VoteInfo.YES, _DEBOUNCE_MS
        ),
    )

    loop = uasyncio.get_event_loop()
    loop.create_task(consume_queue(queue))
    loop.run_forever()


main()
