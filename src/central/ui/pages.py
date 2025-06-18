"""Defines the UI pages for the application."""

from consts import ReportingMode, TimingMode
from ui.core import Page
from ui.widgets import TimeStepperPage, get_page
from vote_session import VoteSession


def build_pages(session: VoteSession, timer_pg: TimeStepperPage) -> list[Page]:
    """Build the pages for the UI."""
    return [
        get_page(
            [(5, ["Start"], session.spawn), (1, ["Settings"], None)],
            with_back_button=False,
        ),
        get_page([(2, ["Reporting"], None), (3, ["Timing"], None)]),
        get_page(
            [
                (
                    2,
                    ["Public"],
                    lambda: session.set_reporting_mode(ReportingMode.PUBLIC),
                ),
                (
                    2,
                    ["Anonymous"],
                    lambda: session.set_reporting_mode(ReportingMode.ANONYMOUS),
                ),
            ],
            with_ok_button=True,
            selectable=True,
        ),
        get_page(
            [
                (3, ["Infinite"], lambda: session.set_timing_mode(TimingMode.INFINITE)),
                (4, ["Timed"], lambda: session.set_timing_mode(TimingMode.TIMED)),
            ],
            with_ok_button=True,
            selectable=True,
        ),
        timer_pg,
        get_page([(6, ["Right: Yes", "Left: No"], None)], with_back_button=False),
        get_page(
            [(7, session.voting_screen_lines, session.end)], with_back_button=False
        ),
        get_page(
            [(0, session.voting_results_screen_lines, session.reset)],
            with_back_button=False,
        ),
    ]
