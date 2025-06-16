"""Module containing the BleVoteController class for ESP32 BLE voting.

ble_vote_controller.py  --  MicroPython ≥1.20 on ESP32

A tiny helper class to:
  * advertise a custom Vote Service
  * handle connects/disconnects
  * send vote/result messages (notify)
  * receive commands from the central (write)

Your main state machine only needs:
    vote = VoteBLE(name="ESP32-A", on_rx=rx_callback)
    vote.vote_yes()   # or .vote_no()
    vote.send("ACK")  # arbitrary string/bytes
"""

import struct
from typing import Callable

import bluetooth
from lib.consts import VOTE_NOTIFY_CHAR_UUID, VOTE_SVC_UUID, VOTE_WRITE_CHAR_UUID
from micropython import const

# GATT flags
_FLAG_READ = const(0x0002)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_FLAG_WREN = const(0x0004 | 0x0008)  # write / write-no-response

# ---------- BLE IRQ event codes ----------
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)


# ---------- advertising helper ----------
def _adv_payload(
    name: bytes, services: list[bluetooth.UUID] | None = None
) -> bytearray:
    """Minimal advertising payload generator."""
    payload = bytearray()

    def _append(t: int, val: bytes) -> None:
        payload.extend(struct.pack("BB", len(val) + 1, t) + val)

    _append(0x01, b"\x06")  # Flags: general discoverable, BR/EDR not supported
    _append(0x09, name)  # Complete Local Name
    if services:
        for uuid in services:
            b = bytes(uuid)  # type: ignore[reportArgumentType]
            _append(0x03 if len(b) == 2 else 0x07, b)
    return payload


# ==================================================
class BleVoteController:
    """Encapsulates BLE functionality for an ESP32 vote controller peripheral."""

    def __init__(
        self,
        ble: bluetooth.BLE | None = None,
        name: str = "ESP32-Vote",
        on_rx: Callable[[bytes], None] | None = None,
        adv_interval_us: int = 500_000,
    ):
        """Initialize the BLE vote service."""
        self._ble = ble or bluetooth.BLE()
        self._ble.active(True)

        # Register service
        self._tx_handle, self._rx_handle = self._register_gatt()
        self._connections: set[memoryview[int]] = set()
        self._on_rx = on_rx

        # Set up IRQ handler *after* registry so handles are valid
        self._ble.irq(self._irq)

        # Start advertising
        self._payload = _adv_payload(name.encode(), [VOTE_SVC_UUID])
        self._advertise(interval_us=adv_interval_us)
        print(f"BLE ready: advertising as '{name}'")

    # ---------- Public helpers ----------

    def send(self, msg: bytes) -> None:
        """Notify all connected centrals with a UTF-8 string or raw bytes."""
        for conn in self._connections:
            try:
                self._ble.gatts_notify(int(conn), self._tx_handle, msg)  # type: ignore[reportCallIssue]
            except OSError:  # Link might have dropped
                self._connections.discard(conn)

    # ---------- Internal plumbing ----------

    def _register_gatt(self) -> tuple[memoryview[int], memoryview[int]]:
        tx_char = (
            VOTE_NOTIFY_CHAR_UUID,
            _FLAG_NOTIFY,
        )
        rx_char = (
            VOTE_WRITE_CHAR_UUID,
            _FLAG_WREN,
        )
        vote_service = (VOTE_SVC_UUID, (tx_char, rx_char))
        # [[tx_handle, rx_handle]]
        ((tx_handle, rx_handle),) = self._ble.gatts_register_services((vote_service,))
        return tx_handle, rx_handle

    def _advertise(self, interval_us: int = 500_000) -> None:
        """(Re)start advertising.

        Ignore the “already advertising” race that can
        happen immediately after a disconnect.
        """
        try:
            self._ble.gap_advertise(None)  # type: ignore[reportArgumentType] stop if already running
        except OSError:
            pass  # no advert → ENOENT, ignore

        try:
            self._ble.gap_advertise(interval_us, self._payload)
        except OSError as err:
            if err.args[0] != -30:  # BLE_HS_EALREADY
                raise  # re-raise unknown errors

    def _irq(self, event: int, data: tuple[memoryview[int], ...]) -> None:
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            print("Central connected:", conn_handle)

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            print("Central disconnected:", conn_handle)
            # Resume advertising so another central can connect
            self._advertise()

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data
            if attr_handle == self._rx_handle:
                raw = self._ble.gatts_read(self._rx_handle)
                if self._on_rx:
                    try:
                        self._on_rx(raw)  # user callback
                    except Exception as e:
                        print("RX callback error:", e)
