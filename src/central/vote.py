"""Module containing the VoteCentral class for RP2350 BLE voting.

vote.py  --  MicroPython central-role helper for the “vote” project

Usage example
    import vote, uasyncio as asyncio

    def got_vote(node_id: int, payload: bytes) -> None:
        print("Node", node_id, "sent", payload)

    vc = vote_central.VoteCentral(on_rx=got_vote, max_peers=5)
    vc.auto_connect()           # start scanning/connecting in background

    asyncio.run(asyncio.sleep(60))  # keep main script alive
"""

# TODO: fix name at top
# TODO: fix names of vote files

import struct
from collections.abc import Callable
from typing import cast

import bluetooth
from micropython import const

# -------------------------------------------------
#  UUIDs – **must match** the ESP32 peripheral file
# -------------------------------------------------
_VOTE_SVC_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
_TX_CHAR_UUID = bluetooth.UUID(
    "12345678-1234-5678-1234-56789abcdef1"
)  # ESP32 ➜ RP2350 (notify)
_RX_CHAR_UUID = bluetooth.UUID(
    "12345678-1234-5678-1234-56789abcdef2"
)  # RP2350 ➜ ESP32 (write)

_VOTE_SVC_UUID_BIN: bytes = cast(bytes, _VOTE_SVC_UUID)  # for fast adv-scan matching

# -------------------------------------------------
#  BLE IRQ event codes (central side)
# -------------------------------------------------
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_NOTIFY = const(18)


# -------------------------------------------------
class _Peer:
    """Book-keeping for each connected ESP32."""

    def __init__(self, addr: bytes) -> None:
        self.addr: bytes = addr
        self.conn_handle: int = -1
        self.tx_handle: memoryview[int] | None = None  # ESP32 ➜ us
        self.rx_handle: memoryview[int] | None = None  # us ➜ ESP32
        self.svc_range: tuple[int, int] | None = None  # (start_handle, end_handle)


# -------------------------------------------------
class BleVoteManager:
    """Encapsulates BLE functionality for an RP2350 vote manager module.

    Central-side helper that
      * scans and auto-connects to advertising Vote ESP32s
      * subscribes to their notifications (votes / status)
      * lets you send commands back
    """

    def __init__(
        self,
        ble: bluetooth.BLE | None = None,
        *,
        on_rx: Callable[[int, bytes], None] | None = None,
        max_peers: int = 5,
    ) -> None:
        """Initialize the VoteCentral instance.

        Args:
            ble (bluetooth.BLE):  pass an existing bluetooth.BLE() instance, or None to create one
            on_rx (Callable[[int, bytes], None]): callback(conn_handle, payload) on every incoming notification
            max_peers (int): number of ESP32s to connect to
        """
        self._ble: bluetooth.BLE = ble or bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)

        self._on_rx: Callable[[int, bytes], None] | None = on_rx
        self._max_peers: int = max_peers
        self._peers: dict[memoryview[int], _Peer] = {}  # conn_handle → _Peer
        self._addr_to_conn: dict[bytes, int] = {}  # addr → conn_handle

    # -------------------------------------------------
    #  Public helpers
    # -------------------------------------------------
    def auto_connect(self, scan_ms: int = 0) -> None:
        """Start scanning for vote controller ESP32s and connect automatically.

        Whenever an advertising packet with the Vote service UUID
        appears, connect automatically until `max_peers` links are active.

        Args:
            scan_ms (int):  duration in ms to scan (0 = scan forever)
        """
        self._ble.gap_scan(scan_ms, 30000, 30000)  # window/interval = 30 ms

    def send(self, conn_handle: memoryview[int], msg: str | bytes) -> None:
        """Write a command to a single ESP32 (does NOT await a response)."""
        peer = self._peers.get(conn_handle)
        if not peer or peer.rx_handle is None:
            return
        if isinstance(msg, str):
            msg = msg.encode()
        self._ble.gattc_write(conn_handle, peer.rx_handle, msg, 1)  # WRITE_NO_RESPONSE

    def broadcast(self, msg: str | bytes) -> None:
        """Write the same command to every connected ESP32."""
        for ch in list(self._peers):
            self.send(ch, msg)

    # -------------------------------------------------
    #  Internal: BLE event handler
    # -------------------------------------------------
    def _handle_scan_result(self, data: tuple) -> None:
        addr_type, addr, adv_type, rssi, adv_data = data
        if (
            len(self._peers) < self._max_peers
            and _VOTE_SVC_UUID_BIN in adv_data
            and addr not in self._addr_to_conn
        ):
            # Stop scanning momentarily to initiate a connection
            self._ble.gap_scan(None)  # type: ignore[reportArgumentType]
            self._ble.gap_connect(addr_type, addr)  # Non-blocking
            print("Connecting to", self._addr_hex(addr))

    def _handle_peripheral_connect(self, data: tuple) -> None:
        conn_handle, addr_type, addr, status = data
        if status != 0:
            print("Connect failed", status)
            self._ble.gap_scan(0)  # resume scan
            return
        peer = _Peer(addr)
        peer.conn_handle = conn_handle
        self._peers[conn_handle] = peer
        self._addr_to_conn[addr] = conn_handle
        print("Connected", conn_handle)
        # Discover Vote service
        self._ble.gattc_discover_services(conn_handle)

    def _handle_gattc_service_result(self, data: tuple) -> None:
        conn_handle, start_handle, end_handle, uuid = data
        if uuid == _VOTE_SVC_UUID:
            self._peers[conn_handle].svc_range = (start_handle, end_handle)

    def _handle_gattc_service_done(self, data: tuple) -> None:
        conn_handle, status = data
        peer = self._peers.get(conn_handle)
        if not peer or status != 0 or peer.svc_range is None:
            return
        start, end = peer.svc_range
        self._ble.gattc_discover_characteristics(conn_handle, start, end)

    def _handle_gattc_characteristic_result(self, data: tuple) -> None:
        conn_handle, def_handle, value_handle, properties, uuid = data
        peer = self._peers.get(conn_handle)
        if not peer:
            return
        if uuid == _TX_CHAR_UUID:
            peer.tx_handle = value_handle
        elif uuid == _RX_CHAR_UUID:
            peer.rx_handle = value_handle

    def _handle_gattc_characteristic_done(self, data: tuple) -> None:
        conn_handle, status = data
        peer = self._peers.get(conn_handle)
        if not peer or status != 0 or peer.tx_handle is None:
            return
        # Enable notifications: write 0x0001 to CCCD (tx_handle + 1)
        cccd = cast(int, peer.tx_handle) + 1
        self._ble.gattc_write(
            conn_handle, cast(memoryview[int], cccd), struct.pack("<h", 1), 1
        )
        print("Subscribed to", conn_handle)
        # Resume scanning if we need more peers
        if len(self._peers) < self._max_peers:
            self._ble.gap_scan(0)

    def _handle_gattc_notify(self, data: tuple) -> None:
        conn_handle, value_handle, notify_data = data
        if self._on_rx:
            self._on_rx(conn_handle, notify_data)

    def _handle_peripheral_disconnect(self, data: tuple) -> None:
        conn_handle, addr_type, addr, reason = data
        print("Disconnected", conn_handle, "reason", reason)
        self._peers.pop(conn_handle, None)
        self._addr_to_conn.pop(addr, None)
        # Scan again to replace the lost link
        self._ble.gap_scan(0)

    def _irq(self, event: int, data: tuple) -> None:
        if event == _IRQ_SCAN_RESULT:
            self._handle_scan_result(data)
        elif event == _IRQ_PERIPHERAL_CONNECT:
            self._handle_peripheral_connect(data)
        elif event == _IRQ_GATTC_SERVICE_RESULT:
            self._handle_gattc_service_result(data)
        elif event == _IRQ_GATTC_SERVICE_DONE:
            self._handle_gattc_service_done(data)
        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            self._handle_gattc_characteristic_result(data)
        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
            self._handle_gattc_characteristic_done(data)
        elif event == _IRQ_GATTC_NOTIFY:
            self._handle_gattc_notify(data)
        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            self._handle_peripheral_disconnect(data)

    # -------------------------------------------------
    #  Utility
    # -------------------------------------------------
    @staticmethod
    def _addr_hex(addr: bytes) -> str:
        return ":".join(f"{b:02X}" for b in addr)
