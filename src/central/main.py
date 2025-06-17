"""Main entry point for the central module."""

from typing import Any, Callable

import machine
import micropython
import uasyncio
from ble_vote_manager import BleVoteManager
from encoder.rotary_irq_rp2 import RotaryIRQ
from lcd.ili9341 import Display
from lib.consts import VoteCommand, VoteInfo
from lib.threadsafe_queue import ThreadSafeQueue
from lib.utils import get_db_button_irq
from machine import SPI, Pin
from ui.core import Router
from ui.widgets import TimeStepperPage, get_page

# Allocate buffer for hard-crash tracebacks inside IRQ
micropython.alloc_emergency_exception_buf(100)

loop = uasyncio.get_event_loop()


class ReportingMode:
    """Enum-like class for reporting modes."""

    PUBLIC = "Public"
    ANONYMOUS = "Anonymous"


class TimingMode:
    """Enum-like class for timing modes."""

    INFINITE = "Infinite"
    TIMED = "Timed"


DISPLAY = Display(
    SPI(
        0,
        baudrate=40_000_000,
        sck=Pin("GP18", Pin.OUT),
        mosi=Pin("GP19", Pin.OUT),
        miso=Pin("GP4", Pin.IN, Pin.PULL_DOWN),
    ),
    dc=Pin("GP7", Pin.OUT),
    cs=Pin("GP5", Pin.OUT),
    rst=Pin("GP6", Pin.OUT),
)

reporting_mode = ReportingMode.PUBLIC


def get_set_reporting_mode_fxn(mode: str) -> Callable[[], None]:
    """Get a function to set the reporting mode for the voting system."""

    def set_reporting_mode() -> None:
        """Set the reporting mode for the voting system."""
        global reporting_mode
        reporting_mode = mode

    return set_reporting_mode


timing_mode = TimingMode.INFINITE


def get_set_timing_mode_fxn(mode: str) -> Callable[[], None]:
    """Get a function to set the timing mode for the voting system."""

    def set_timing_mode() -> None:
        """Set the timing mode for the voting system."""
        global timing_mode
        timing_mode = mode

    return set_timing_mode


manager: BleVoteManager | None = None
tutorial_timer: machine.Timer | None = None


def start_tutorial(_: int) -> None:
    """Start the tutorial."""
    global manager, tutorial_timer
    if not manager:
        return
    manager.stop_scanning()
    tutorial_timer = machine.Timer(
        -1,
        mode=machine.Timer.ONE_SHOT,
        period=3000,
        callback=lambda _: micropython.schedule(_handle_button_press, 0),
    )


def _get_vote_results(vote_record: dict[int, int]) -> list[str]:
    """Get the results of the voting."""
    if not vote_record:
        return ["No votes"]
    yes_count = sum(1 for v in vote_record.values() if v == VoteInfo.YES)
    no_count = sum(1 for v in vote_record.values() if v == VoteInfo.NO)
    return [f"Yes: {yes_count}", f"No: {no_count}", f"Total: {len(vote_record)}"]


voting_results_screen_lines = []


def end_vote() -> None:
    """End the voting process."""
    global \
        manager, \
        voting_timer, \
        vote_record, \
        voting_results_screen_lines, \
        voting_screen_lines
    if not manager or not voting_timer:
        return

    voting_timer.deinit()
    voting_timer = None

    # Send stop command to all connected peers
    manager.broadcast(VoteCommand.STOP)

    voting_results_screen_lines = _get_vote_results(vote_record)


def reset_vote_state() -> None:
    """Reset the voting state and prepare for a new vote."""
    global voting, manager, vote_record, voting_results_screen_lines
    if not manager:
        return

    vote_record.clear()
    voting_results_screen_lines.clear()
    manager.broadcast(VoteCommand.INDICATE_NONE)  # indicate none votes to all peers

    voting = False
    manager.resume_scanning()


def _get_time_as_string(seconds: int) -> str:
    """Get the current time as a string in MM:SS format."""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02}:{seconds:02}"


def _scheduled_display(_: Any) -> None:
    """Update the display from the scheduler."""
    ROUTER.current_page.display()


voting_timer: machine.Timer | None = None
voting_time_left = 0
voting_screen_lines = []
ELLIPSIS = "..."


def _voting_timer_tick() -> None:
    """Tick function for the voting timer.

    Once all votes are in or timer is done, send stop command, indicate none
    """
    global manager, timing_mode, vote_record, voting_timer, voting_time_left
    if not manager or not voting_timer:
        return

    if timing_mode == TimingMode.TIMED:
        voting_time_left -= 1

    if voting_time_left < 0 or len(vote_record) == manager.num_peers:
        micropython.schedule(_handle_button_press, 0)

    if timing_mode == TimingMode.TIMED:
        voting_screen_lines[0] = _get_time_as_string(voting_time_left)
    else:
        if voting_screen_lines[0][-3:] == ELLIPSIS:
            voting_screen_lines[0] = "Waiting"
        else:
            voting_screen_lines[0] += "."
    micropython.schedule(_scheduled_display, 0)


def start_vote() -> None:
    """Start the voting process."""
    global \
        manager, \
        tutorial_timer, \
        voting, \
        voting_timer, \
        voting_screen_lines, \
        voting_time_left
    if not manager or not tutorial_timer:
        return
    tutorial_timer.deinit()
    tutorial_timer = None

    manager.broadcast(VoteCommand.START)  # send start command to all connected peers
    voting = True

    voting_time_left = get_timer_s() if timing_mode == TimingMode.TIMED else 1

    voting_screen_lines.clear()
    if timing_mode == TimingMode.TIMED:
        voting_screen_lines.append(_get_time_as_string(voting_time_left))
    else:
        voting_screen_lines.append("Waiting")

    voting_timer = machine.Timer(
        -1,
        mode=machine.Timer.PERIODIC,
        period=1000,
        callback=lambda _: _voting_timer_tick(),
    )


def spawn_vote() -> None:
    """Spawn a new vote and start the voting process."""
    micropython.schedule(start_tutorial, 0)


TIMER_STEPPER_PAGE = TimeStepperPage(4, 1, 30)
ROUTER = Router(
    DISPLAY,
    [
        get_page(
            [
                (1, ["Settings"], None),
                (5, ["Start"], spawn_vote),
            ],
            with_back_button=False,
        ),
        get_page([(2, ["Reporting"], None), (3, ["Timing"], None)]),
        get_page(
            [
                (2, ["Public"], get_set_reporting_mode_fxn("Public")),
                (2, ["Anonymous"], get_set_reporting_mode_fxn("Anonymous")),
            ],
            with_ok_button=True,
            selectable=True,
        ),
        get_page(
            [
                (3, ["Infinite"], get_set_timing_mode_fxn("Infinite")),
                (4, ["Timed"], get_set_timing_mode_fxn("Timed")),
            ],
            with_ok_button=True,
            selectable=True,
        ),
        TIMER_STEPPER_PAGE,
        get_page(
            [(6, ["Right: Yes", "Left: No"], None)],
            with_back_button=False,
        ),
        get_page(
            [(7, voting_screen_lines, end_vote)],
            with_back_button=False,
        ),
        get_page(
            [(0, voting_results_screen_lines, reset_vote_state)],
            with_back_button=False,
        ),
    ],
)


def get_timer_s() -> int:
    """Get the timer value in seconds."""
    return TIMER_STEPPER_PAGE.minutes * 60 + TIMER_STEPPER_PAGE.seconds


queue: ThreadSafeQueue  # forward declaration; filled in main()
voting: bool = False  # indicates if voting is currently active
vote_record: dict[int, int] = {}  # maps connection handles to vote values


async def consume_queue(q: ThreadSafeQueue) -> None:
    """Consume vote info tuples from the queue and updates LEDs accordingly."""
    while True:
        conn_handle, payload = await q.get()  # await - no busy polling
        vote_record[conn_handle] = payload
        if reporting_mode == ReportingMode.PUBLIC:
            # Reflect the vote back to the controller
            if manager:
                if payload == VoteInfo.YES:
                    manager.send(conn_handle, VoteCommand.INDICATE_YES)
                elif payload == VoteInfo.NO:
                    manager.send(conn_handle, VoteCommand.INDICATE_NO)
                else:
                    manager.send(conn_handle, VoteCommand.INDICATE_NONE)


ENCODER = RotaryIRQ(clk_pin="GP2", dt_pin="GP3", pull_up=True)
ENCODER_BTN = Pin("GP10", Pin.IN, Pin.PULL_UP)


old_encoder_val = ENCODER.value()


def _encoder_callback() -> None:
    global old_encoder_val
    difference = ENCODER.value() - old_encoder_val
    old_encoder_val += difference
    micropython.schedule(_handle_encoder_difference, difference)


def _handle_encoder_difference(value_difference: int) -> None:
    if value_difference == 1:
        ROUTER.current_page.focus_next()
    elif value_difference == -1:
        ROUTER.current_page.focus_previous()
    ROUTER.current_page.display()


_BTN_DEBOUNCE_MS = micropython.const(400)  # mechanical bounce time
last_btn_time = 0


def _handle_button_press(_: Any) -> None:
    global tutorial_timer
    if tutorial_timer:
        start_vote()
    ROUTER.current_page.select()
    ROUTER.current_page.display()


def main() -> None:
    """Main entry point for the controller application."""
    global loop, queue, manager, voting
    queue = ThreadSafeQueue(16)

    manager = BleVoteManager(
        on_rx=lambda conn_handle, payload: queue.put_sync((conn_handle, payload))
        if voting
        else None,
    )

    ROUTER.current_page.display()
    ENCODER.add_listener(_encoder_callback)
    ENCODER_BTN.irq(
        trigger=Pin.IRQ_FALLING,
        handler=get_db_button_irq(
            _handle_button_press, ENCODER_BTN, 0, _BTN_DEBOUNCE_MS
        ),
    )

    loop.create_task(consume_queue(queue))
    loop.run_forever()


main()
