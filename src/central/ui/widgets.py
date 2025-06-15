"""Module containing UI widgets for the application."""

from lcd.xglcd_font import XglcdFont
from micropython import const
from ui.core import Component, Page

_DISP_WIDTH = const(320)
_DISP_HEIGHT = const(240)

FONT = XglcdFont("lcd/Robotron13x21.c", 13, 21)
_LETTER_SPACING = const(1)  # Spacing between letters in pixels
_LINE_SPACING = const(2)  # Spacing between lines in pixels
_PADDING_X = const(5)  # Padding on the left and right of the card
_PADDING_Y = const(5)  # Padding on the top and bottom of the card


class Card(Component):
    """A rectangular card widget for displaying content."""

    def __init__(
        self,
        next_page: int,
        x: int,
        y: int,
        width: int,
        height: int,
        lines: list[str] = [],
    ) -> None:
        """Initialize the card with position, size, and next page.

        `x`,`y`, `width`, and `height` are in landscape orientation, with the origin at the top-left corner
        of the screen, and (x, y) corresponding to the top-left corner of the card.
        """
        super().__init__(next_page)
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

    def display(self, focused: bool) -> None:
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
                color=0xFFFF,  # always draw text in white
                spacing=_LETTER_SPACING,
                landscape=True,
            )

        # Card outline
        card_width = max_width + _PADDING_X * 2
        card_height = total_text_height + _PADDING_Y * 2
        portrait_x, portrait_y = self._get_as_portrait(
            min_x - _PADDING_X + card_width, start_y - _PADDING_Y
        )
        self.router.display.draw_rectangle(
            portrait_x,
            portrait_y,
            card_height,
            card_width,
            color=0xFFFF if focused else 0x0000,  # white if focused, black otherwise
        )


_BACK_WIDTH = const(80)
_BACK_HEIGHT = const(30)


class BackButton(Card):
    """A back button widget that navigates to the previous page."""

    def __init__(self) -> None:
        """Initialize the back button with position and next page."""
        super().__init__(
            0, 0, _DISP_HEIGHT - _BACK_HEIGHT, _BACK_WIDTH, _BACK_HEIGHT, ["Back"]
        )

    def select(self) -> None:
        """Navigate to the previous page."""
        if not self.router:
            print("No router available to navigate back.")
            return
        self.router.go_back()


def get_page(
    card_info: list[tuple[int, list[str]]],
    *,
    with_back_button: bool = True,
) -> Page:
    """Create a Page whose Cards span the full height and share the width equally.

    Args:
        card_info (list[tuple[int, list[str]]]): [(next_page, lines), ...] for each card to build.
        with_back_button (bool): If True, adds a BackButton at the bottom-left.
    """
    if not card_info:
        raise ValueError("card_info must contain at least one entry")

    # Reserve vertical space for the back button if it will be shown
    usable_height = _DISP_HEIGHT - (_BACK_HEIGHT if with_back_button else 0)
    num_cards = len(card_info)

    # Base width for every card (integer division)
    base_width = _DISP_WIDTH // num_cards

    components: list[Component] = []

    for idx, (next_page, lines) in enumerate(card_info):
        # X coordinate for the left edge of this card
        x = idx * base_width

        # Make the FINAL card absorb any leftover pixels
        width = (_DISP_WIDTH - x) if idx == num_cards - 1 else base_width

        components.append(Card(next_page, x, 0, width, usable_height, lines))

    if with_back_button:
        components.append(BackButton())

    return Page(components)
