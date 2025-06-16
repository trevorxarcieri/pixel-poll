"""Module containing UI widgets for the application."""

from typing import Callable

from lcd.xglcd_font import XglcdFont
from micropython import const
from ui.core import (
    BACKGROUND,
    FOCUS_OUTLINE,
    TEXT_NORMAL,
    TEXT_SELECTED,
    Component,
    Page,
)

_DISP_WIDTH = const(320)
_DISP_HEIGHT = const(240)

_FONT_HEIGHT = const(21)  # Height of the font in pixels
FONT = XglcdFont("lcd/Robotron13x21.c", 13, _FONT_HEIGHT)
_LETTER_SPACING = const(1)  # Spacing between letters in pixels
_LINE_SPACING = const(2)  # Spacing between lines in pixels
_PADDING_X = const(10)  # Padding on the left and right of the card
_PADDING_Y = const(10)  # Padding on the top and bottom of the card


class Card(Component):
    """A rectangular card widget for displaying content."""

    def __init__(
        self,
        next_page: int,
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        on_select: Callable[[], None] | None = None,
        selectable: bool = True,
        lines: list[str] = [],
    ) -> None:
        """Initialize the card with position, size, and next page.

        `x`,`y`, `width`, and `height` are in landscape orientation, with the origin at the top-left corner
        of the screen, and (x, y) corresponding to the top-left corner of the card.
        """
        super().__init__(next_page, on_select=on_select, selectable=selectable)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.lines = lines

    def _get_as_portrait(self, x: int, y: int) -> tuple[int, int]:
        """Convert landscape coordinates (x, y) to portrait coordinates."""
        if not self.router:
            print("No router available to display the card.")
            return (-1, -1)
        return y, _DISP_WIDTH - x

    def display(self, *, focused: bool, selected: bool) -> None:
        """Display the card widget, highlighting if focused."""
        if not self.router:
            print("No router available to display the card.")
            return

        # Center-aligned text
        line_height = FONT.height + _LINE_SPACING
        total_text_height = len(self.lines) * line_height - _LINE_SPACING

        # Y-position of the first line so that the block of lines is vertically centred
        start_y = self.y + (self.height - total_text_height) // 2
        max_width = 0
        min_x = _DISP_WIDTH  # start with a large value to find the minimum

        for idx, line in enumerate(self.lines):
            if isinstance(line, list):
                # If the line is a list, join it into a single string
                clean = "".join(line).upper()
            else:
                # Otherwise, treat it as a single string
                clean = line.upper()

            # Pixel width of this line (character count × glyph width)
            line_width = FONT.measure_text(clean, _LETTER_SPACING) - _LETTER_SPACING
            max_width = max(max_width, line_width)

            # X-position so the line is horizontally centred
            start_x = self.x + (self.width - line_width) // 2
            min_x = min(min_x, start_x)

            # Draw the line
            text_x, text_y = self._get_as_portrait(start_x, start_y + idx * line_height)
            self.router.display.draw_text(
                text_x,
                text_y,
                clean,
                FONT,
                color=TEXT_NORMAL if not selected else TEXT_SELECTED,
                background=BACKGROUND,
                spacing=_LETTER_SPACING,
                landscape=True,
            )

        # Card outline
        card_width = max_width + _PADDING_X * 2
        card_height = total_text_height + _PADDING_Y * 2
        portrait_x, portrait_y = self._get_as_portrait(
            min_x - _PADDING_X + card_width, start_y - _PADDING_Y
        )
        if focused:
            self.router.display.draw_rectangle(
                portrait_x,
                portrait_y,
                card_height,
                card_width,
                color=FOCUS_OUTLINE,
            )


_BACK_WIDTH = const(80)
_BTN_HEIGHT = const(_FONT_HEIGHT + _PADDING_Y * 2)


class BackButton(Card):
    """A back button widget that navigates to the previous page."""

    def __init__(self) -> None:
        """Initialize the back button with position and next page."""
        super().__init__(
            0,
            0,
            _DISP_HEIGHT - _BTN_HEIGHT,
            _BACK_WIDTH,
            _BTN_HEIGHT,
            selectable=False,
            lines=["Back"],
        )

    def select(self) -> None:
        """Navigate to the previous page."""
        if not self.router:
            print("No router available to navigate back.")
            return
        self.router.go_back()


_OK_WIDTH = const(48)


class OkButton(Card):
    """An ok button widget that submits some current information."""

    def __init__(self) -> None:
        """Initialize the ok button with position and next page."""
        super().__init__(
            0,
            _DISP_WIDTH - _OK_WIDTH,
            _DISP_HEIGHT - _BTN_HEIGHT,
            _OK_WIDTH,
            _BTN_HEIGHT,
            selectable=False,
            lines=["Ok"],
        )


def get_page(
    card_info: list[tuple[int, list[str], Callable[[], None] | None]],
    *,
    with_back_button: bool = True,
    with_ok_button: bool = False,
    selectable: bool = False,
) -> Page:
    """Create a Page whose Cards span the full height and share the width equally.

    Args:
        card_info (list[tuple[int, list[str]]], Callable | None): [(next_page, lines, on_select), ...] for each card to build.
        with_back_button (bool): If True, adds a BackButton at the bottom-left.
        with_ok_button (bool): If True, adds an OkButton at the bottom-right.
        selectable (bool): If True, allows selecting cards on the page.
    """
    if not card_info:
        raise ValueError("card_info must contain at least one entry")

    # Reserve vertical space for the back button if it will be shown
    num_cards = len(card_info)

    # Base width for every card (integer division)
    base_width = _DISP_WIDTH // num_cards

    components: list[Component] = []

    for idx, (next_page, lines, on_select) in enumerate(card_info):
        # X coordinate for the left edge of this card
        x = idx * base_width

        # Make the FINAL card absorb any leftover pixels
        width = (_DISP_WIDTH - x) if idx == num_cards - 1 else base_width

        components.append(
            Card(next_page, x, 0, width, _DISP_HEIGHT, on_select=on_select, lines=lines)
        )

    if with_ok_button:
        components.append(OkButton())
    if with_back_button:
        components.append(BackButton())

    return Page(components, selectable=selectable)


_TIME_DIGITS_WIDTH = const(50)
_TIME_COLON_WIDTH = const(15)


class TimeStepperPage(Page):
    """A page with a numeric stepper for selecting a number."""

    def __init__(self, page_ind: int, minutes: int, seconds: int) -> None:
        """Initialize the numeric stepper page."""
        self.minutes = minutes
        self.seconds = seconds

        center_x = _DISP_WIDTH // 2
        colon_x = center_x - _TIME_COLON_WIDTH // 2
        left_digits_x = colon_x - _TIME_DIGITS_WIDTH
        right_digits_x = colon_x + _TIME_COLON_WIDTH

        self.minutes_lines = [f"{minutes:02}"]
        self.seconds_lines = [f"{seconds:02}"]
        super().__init__(
            [
                Card(
                    page_ind,
                    left_digits_x,
                    0,
                    _TIME_DIGITS_WIDTH,
                    _DISP_HEIGHT,
                    lines=self.minutes_lines,
                ),
                Card(
                    page_ind,
                    colon_x,
                    0,
                    _TIME_COLON_WIDTH,
                    _DISP_HEIGHT,
                    selectable=False,
                    lines=[":"],
                ),
                Card(
                    page_ind,
                    right_digits_x,
                    0,
                    _TIME_DIGITS_WIDTH,
                    _DISP_HEIGHT,
                    lines=self.seconds_lines,
                ),
                OkButton(),
                BackButton(),
            ],
            selectable=True,
        )
        self.selected = -1

    def select(self) -> None:
        """Select the focused element on the page."""
        if (self.focus == 0 and self.selected == 0) or (
            self.focus == 2 and self.selected == 2
        ):
            self.selected = -1  # Deselect if already selected
        elif self.selectable and self.elements[self.focus].selectable:
            self.selected = self.focus

        self.elements[self.focus].select()
        if self.focus in (3, 4):  # OkButton or BackButton
            self.focus = 0  # reset focus after selection

    def update_minutes(self, inc: int) -> None:
        """Update the minutes value and display."""
        self.minutes += inc
        self.minutes %= 100  # Wrap around if minutes exceed 99
        self.minutes_lines[0] = f"{self.minutes:02}"

    def update_seconds(self, inc: int) -> None:
        """Update the seconds value and display."""
        self.seconds += inc
        self.seconds %= 60  # Wrap around if seconds exceed 59
        self.seconds_lines[0] = f"{self.seconds:02}"

    def focus_next(self) -> None:
        """Move focus to the next element on the page."""
        if self.selected == -1:
            super().focus_next()
            return
        if self.selected == 0:
            self.update_minutes(1)
        elif self.selected == 2:
            self.update_seconds(1)

    def focus_previous(self) -> None:
        """Move focus to the previous element on the page."""
        if self.selected == -1:
            super().focus_previous()
            return
        if self.selected == 0:
            self.update_minutes(-1)
        elif self.selected == 2:
            self.update_seconds(-1)
