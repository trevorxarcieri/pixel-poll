"""Main entry point for the central module."""

import uasyncio as asyncio
from ble_vote_manager import BleVoteManager
from consts import BTN_DEBOUNCE_MS, ReportingMode
from hardware import attach_encoder_navigation, init_display, init_encoder
from lib.consts import VoteCommand, VoteInfo
from lib.threadsafe_queue import ThreadSafeQueue
from lib.utils import get_db_button_irq
from machine import Pin
from ui.core import Router
from ui.pages import build_pages
from ui.widgets import TimeStepperPage
from vote_session import VoteSession

DISPLAY = init_display()
ENCODER, ENCODER_BTN = init_encoder()

TIMER_STEPPER_PAGE = TimeStepperPage(4, 0, 30)

ROUTER = Router(DISPLAY, [])  # placeholder until pages built
attach_encoder_navigation(ENCODER, ROUTER)

manager = BleVoteManager()
session = VoteSession(manager, ROUTER, TIMER_STEPPER_PAGE)

queue: ThreadSafeQueue = ThreadSafeQueue(16)


async def consume_queue() -> None:
    """Pull vote tuples off the ThreadSafeQueue and update session state."""
    while True:
        conn_handle, payload = await queue.get()
        session.vote_record[conn_handle] = payload

        # Reflect the vote back to the peripheral if reporting is PUBLIC
        if session.reporting_mode == ReportingMode.PUBLIC:
            if payload == VoteInfo.YES:
                manager.send(conn_handle, VoteCommand.INDICATE_YES)
            elif payload == VoteInfo.NO:
                manager.send(conn_handle, VoteCommand.INDICATE_NO)
            else:
                manager.send(conn_handle, VoteCommand.INDICATE_NONE)


manager.set_on_rx(
    lambda conn_handle, payload: queue.put_sync((conn_handle, payload))
    if session.voting
    else None
)
ROUTER.set_pages(build_pages(session, TIMER_STEPPER_PAGE))

ENCODER_BTN.irq(
    trigger=Pin.IRQ_FALLING,
    handler=get_db_button_irq(
        session.handle_button_press, ENCODER_BTN, 0, BTN_DEBOUNCE_MS
    ),
)


# --- uasyncio entry ---
async def _main() -> None:
    """Main entry point for the central application."""
    loop = asyncio.get_event_loop()
    loop.create_task(consume_queue())  # uses global queue
    ROUTER.current_page.display()
    await loop.run_forever()


asyncio.run(_main())
