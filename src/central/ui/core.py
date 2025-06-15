"""Module for managing the user interface of the application."""

from typing import Protocol

from lcd.ili9341 import Display


class IsRouter(Protocol):
    """Protocol for a router that can navigate between pages."""

    display: Display

    def show_page(self, page_ind: int) -> None:
        """Show a page by its index."""
        ...

    def go_back(self) -> None:
        """Go back to the previous page."""
        ...


class Component:
    """Class for UI components."""

    def __init__(self, nextPage: int):
        """Initialize the component with a name."""
        self.router: IsRouter | None = None
        self.nextPage = nextPage

    def add_router(self, router: IsRouter | None) -> None:
        """Add a router to the component for navigation."""
        self.router = router

    def display(self, focused: bool) -> None:
        """Display the component."""
        raise NotImplementedError("Subclasses should implement this method.")

    def select(self) -> None:
        """Select the component, navigating to the next page."""
        if not self.router:
            print("No router available to select the component.")
            return
        self.router.show_page(self.nextPage)


class Page:
    """Class representing a single page in the UI."""

    def __init__(self, elements: list[Component]):
        """Initialize the page with a list of elements."""
        self.router: IsRouter | None = None
        self.elements = elements
        self.focus = 0

    def add_router(self, router: IsRouter | None) -> None:
        """Add a router to the page for navigation."""
        self.router = router
        for element in self.elements:
            element.add_router(router)

    def display(self) -> None:
        """Display the elements of the page."""
        if not self.router:
            print("No router available to display elements.")
            return
        self.router.display.clear()
        for i, element in enumerate(self.elements):
            element.display(i == self.focus)

    def select(self) -> None:
        """Select the focused element on the page."""
        self.elements[self.focus].select()

    def focus_next(self) -> None:
        """Move focus to the next element on the page."""
        self.focus = (self.focus + 1) % len(self.elements)

    def focus_previous(self) -> None:
        """Move focus to the previous element on the page."""
        self.focus = (self.focus - 1) % len(self.elements)


class Router:
    """Router class to manage navigation between pages in the UI."""

    def __init__(self, display: Display, pages: list[Page]):
        """Initialize the Router with a list of pages."""
        self.display = display
        self.pages = pages
        self.history = [0]  # Start with the first page in history
        for page in self.pages:
            page.add_router(self)

    def show_page(self, page_ind: int) -> None:
        """Show a page by its index and update history."""
        if page_ind < 0 or page_ind >= len(self.pages):
            raise IndexError("Page index out of range")

        self.history.append(page_ind)
        print(f"Showing page: {self.pages[page_ind]}")

    def go_back(self) -> None:
        """Go back to the previous page in history."""
        if len(self.history) <= 1:
            print("No history to go back to.")
            return

        self.history.pop()
        print(f"Going back to page: {self.pages[self.history[-1]]}")

    @property
    def current_page(self) -> Page:
        """Get the current page based on the last entry in history."""
        return self.pages[self.history[-1]]
