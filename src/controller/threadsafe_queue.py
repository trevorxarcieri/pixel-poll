"""Provides ThreadsafeQueue class.

Adapted from https://github.com/peterhinch/micropython-async.

Copyright (c) 2022 Peter Hinch
Released under the MIT License (MIT)

Uses pre-allocated ring buffer: can use list or array
Asynchronous iterator allowing consumer to use async for
"""

import asyncio
from typing import Any


class ThreadSafeQueue:  # MicroPython optimised
    """A thread-safe queue with synchronous and asynchronous methods."""

    def __init__(self, buf: int | list[Any]):
        """Initialize the queue with a fixed-size buffer or a pre-allocated list."""
        self._q = [0 for _ in range(buf)] if isinstance(buf, int) else buf
        self._size = len(self._q)
        self._wi = 0
        self._ri = 0
        self._evput = asyncio.ThreadSafeFlag()  # Triggered by put, tested by get
        self._evget = asyncio.ThreadSafeFlag()  # Triggered by get, tested by put

    def __aiter__(self):
        """Return an asynchronous iterator for the queue."""
        return self

    async def __anext__(self):
        """Return the next item from the queue asynchronously."""
        return await self.get()

    def full(self) -> bool:
        """Check if the queue is full."""
        return ((self._wi + 1) % self._size) == self._ri

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self._ri == self._wi

    def qsize(self) -> int:
        """Return the number of items in the queue."""
        return (self._wi - self._ri) % self._size

    def get_sync(self, block: bool = False) -> Any:
        """Remove and return an item from the queue."""
        if not block and self.empty():
            raise IndexError  # Not allowed to block
        while self.empty():  # Block until an item appears
            pass
        r = self._q[self._ri]
        self._ri = (self._ri + 1) % self._size
        self._evget.set()
        return r

    def put_sync(self, v: Any, block: bool = False) -> None:
        """Add an item to the queue."""
        self._q[self._wi] = v
        self._evput.set()  # Schedule task waiting on get
        if not block and self.full():
            raise IndexError
        while self.full():
            pass  # can't bump ._wi until an item is removed
        self._wi = (self._wi + 1) % self._size

    async def get(self) -> Any:
        """Remove and return an item from the queue asynchronously.

        Usage: `item = await queue.get()`
        """
        while self.empty():
            await self._evput.wait()
        r = self._q[self._ri]
        self._ri = (self._ri + 1) % self._size
        self._evget.set()  # Schedule task waiting on ._evget
        return r

    async def put(self, val: Any) -> None:
        """Add an item to the queue asynchronously.

        Usage: `await queue.put(item)`
        """
        while self.full():  # Queue full
            await self._evget.wait()
        self.put_sync(val)
