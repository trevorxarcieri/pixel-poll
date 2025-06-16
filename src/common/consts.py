"""Common constants used across both the central and peripheral modules."""

import bluetooth

VOTE_SVC_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
VOTE_NOTIFY_CHAR_UUID = bluetooth.UUID(
    "12345678-1234-5678-1234-56789abcdef1"
)  # ESP32 ➜ RP2350 (notify)
VOTE_WRITE_CHAR_UUID = bluetooth.UUID(
    "12345678-1234-5678-1234-56789abcdef2"
)  # RP2350 ➜ ESP32 (write)
