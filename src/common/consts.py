"""Common constants used across both the central and peripheral modules."""

import bluetooth

VOTE_SVC_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
VOTE_NOTIFY_CHAR_UUID = bluetooth.UUID(
    "12345678-1234-5678-1234-56789abcdef1"
)  # ESP32 ➜ RP2350 (notify)
VOTE_WRITE_CHAR_UUID = bluetooth.UUID(
    "12345678-1234-5678-1234-56789abcdef2"
)  # RP2350 ➜ ESP32 (write)


class VoteCommand:
    """Enumeration for vote commands that the vote manager sends to the vote controller."""

    START = bytes(0)
    STOP = bytes(1)
    INDICATE_YES = bytes(2)
    INDICATE_NO = bytes(3)


class VoteInfo:
    """Enumeration for vote information that the vote controller sends to the vote manager."""

    YES = bytes(0)
    NO = bytes(1)
