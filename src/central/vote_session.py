"""Self-contained helper for managing one voting round."""

from typing import Any

import machine
import micropython
from ble_vote_manager import BleVoteManager
from consts import ELLIPSIS, ReportingMode, TimingMode
from lib.consts import VoteCommand, VoteInfo
from ui.core import Router
from ui.widgets import TimeStepperPage


def _get_vote_results(vote_record: dict[int, int]) -> list[str]:
    """Get the results of the voting."""
    if not vote_record:
        return ["No votes"]
    yes_count = sum(1 for v in vote_record.values() if v == VoteInfo.YES)
    no_count = sum(1 for v in vote_record.values() if v == VoteInfo.NO)
    return [f"Yes: {yes_count}", f"No: {no_count}", f"Total: {len(vote_record)}"]


def _get_time_as_string(seconds: int) -> str:
    """Get the current time as a string in MM:SS format."""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02}:{seconds:02}"


class VoteSession:
    """Encapsulates all state, timers, and BLE traffic for a single vote."""

    # --------------------------------------------------------------------- #
    # Construction / state                                                  #
    # --------------------------------------------------------------------- #
    def __init__(
        self,
        manager: BleVoteManager,
        router: Router,
        timer_page: TimeStepperPage,
    ) -> None:
        """Initialize the VoteSession with a manager, router, and timer page."""
        self._mgr = manager
        self._router = router
        self._timer_page = timer_page

        self.vote_record: dict[int, int] = {}
        self.tutorial_timer: machine.Timer | None = None
        self.voting_timer: machine.Timer | None = None
        self.voting_time_left: int = 0
        self.voting: bool = False
        self.reporting_mode: str = ReportingMode.PUBLIC
        self.timing_mode: str = TimingMode.INFINITE

        # Lines used by the router pages
        self.voting_screen_lines: list[str] = []
        self.voting_results_screen_lines: list[str] = []

    # --------------------------------------------------------------------- #
    # Public API                                                            #
    # --------------------------------------------------------------------- #
    def handle_button_press(self, _: Any) -> None:
        """Handler for the rotary-encoder push-button."""
        if self.tutorial_timer:
            self.tutorial_timer.deinit()
            self.tutorial_timer = None
            self.start()  # kick off the vote

        self._router.current_page.select()
        self._router.current_page.display()

    def set_reporting_mode(self, mode: str) -> None:
        """Page callback to switch between Public and Anonymous reporting."""
        self.reporting_mode = mode

    def set_timing_mode(self, mode: str) -> None:
        """Page callback to switch between Infinite and Timed voting."""
        self.timing_mode = mode

    def spawn(self) -> None:
        """Spawn a new voting session.

        Called by the Router's “Start” button.
        Stops scanning, waits 3 s, then behaves as if the physical
        button was pressed (which will in turn call `self.start()`).
        """
        self._mgr.stop_scanning()
        self.tutorial_timer = machine.Timer(
            -1,
            mode=machine.Timer.ONE_SHOT,
            period=3000,
            callback=lambda _: micropython.schedule(self.handle_button_press, 0),
        )

    def start(self, *_unused: int) -> None:
        """Start the voting process."""
        if self.voting_timer:  # already running
            return

        self._mgr.broadcast(VoteCommand.START)
        self.voting = True
        self.voting_time_left = self._initial_time()

        self.voting_screen_lines.clear()
        if self.timing_mode == TimingMode.TIMED:
            self.voting_screen_lines.append(_get_time_as_string(self.voting_time_left))
        else:
            self.voting_screen_lines.append("Waiting")

        # Periodic 1-second tick
        self.voting_timer = machine.Timer(
            -1,
            mode=machine.Timer.PERIODIC,
            period=1000,
            callback=lambda _: self._voting_timer_tick(),
        )

    def end(self) -> None:
        """End the voting process."""
        if not self.voting_timer:
            return

        self.voting_timer.deinit()
        self.voting_timer = None

        self._mgr.broadcast(VoteCommand.STOP)
        self.voting_results_screen_lines[:] = _get_vote_results(self.vote_record)
        self.voting = False

    def reset(self) -> None:
        """Reset the voting state and prepare for a new vote."""
        self.vote_record.clear()
        self.voting_results_screen_lines.clear()
        self._mgr.broadcast(VoteCommand.INDICATE_NONE)
        self.voting = False
        self._mgr.resume_scanning()

    # --------------------------------------------------------------------- #
    # Internal helpers                                                      #
    # --------------------------------------------------------------------- #
    def _initial_time(self) -> int:
        """Return the configured countdown time (in seconds) or 1 for infinite."""
        return (
            self._timer_page.minutes * 60 + self._timer_page.seconds
            if self.timing_mode == TimingMode.TIMED
            else 1
        )

    def _scheduled_display(self, _: Any = 0) -> None:
        """Update the display from a scheduled callback."""
        self._router.current_page.display()

    def _voting_timer_tick(self) -> None:
        """Tick function for the voting timer.

        Once all votes are in or timer is done, send stop command,
        indicate none, and transition to results page.
        """
        if self.timing_mode == TimingMode.TIMED:
            self.voting_time_left -= 1

        # End condition: timeout or every peer has voted
        if self.voting_time_left < 0 or len(self.vote_record) == self._mgr.num_peers:
            micropython.schedule(self.handle_button_press, 0)
            return

        # Update line 0 (count-down or animated Waiting...)
        if self.timing_mode == TimingMode.TIMED:
            self.voting_screen_lines[0] = _get_time_as_string(self.voting_time_left)
        else:
            self.voting_screen_lines[0] = (
                "Waiting"
                if self.voting_screen_lines[0].endswith(ELLIPSIS)
                else self.voting_screen_lines[0] + "."
            )

        # Ask router to redraw
        micropython.schedule(self._scheduled_display, 0)
