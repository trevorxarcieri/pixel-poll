"""Module containing the BleVoteManager class for RP2350 BLE voting.

ble_vote_manager.py  --  MicroPython central-role helper

Usage example
    import vote, uasyncio as asyncio

    def got_vote(node_id: int, payload: bytes) -> None:
        print("Node", node_id, "sent", payload)

    vc = vote_central.VoteCentral(on_rx=got_vote, max_peers=5)
    vc.auto_connect()           # start scanning/connecting in background

    asyncio.run(asyncio.sleep(60))  # keep main script alive
"""

from typing import Callable

import bluetooth
from lib.consts import VOTE_NOTIFY_CHAR_UUID, VOTE_SVC_UUID, VOTE_WRITE_CHAR_UUID
from micropython import const

_ENABLE_NOTIFY = b"\x01\x00"  # pre-packed 0x0001

_VOTE_SVC_UUID_BIN = bytes(VOTE_SVC_UUID)  # type: ignore[reportAssignmentType] for fast adv-scan matching

_FAST_SCAN_WIN_US = const(30_000)  # 30 ms listen time
_FAST_SCAN_INT_US = const(60_000)  # 60 ms between starts  → 50 % duty
_FAST_CONNECT_MS = const(5_000)  # run for 5 s
_SLOW_SCAN_WIN_US = const(15_000)  # 15 ms listen time
_SLOW_SCAN_INT_US = const(300_000)  # 300 ms between starts  → 5 % duty

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
        self.tx_handle: memoryview[int] | None = None  # us ➜ ESP32
        self.rx_handle: memoryview[int] | None = None  # ESP32 ➜ us
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

        self._on_rx = on_rx
        self._max_peers: int = max_peers
        self._peers: dict[int, _Peer] = {}  # conn_handle → _Peer
        self._peer_addrs: list[bytes] = []  # addresses of connected peers
        self._connecting = False
        self._scan_fast_briefly()

    # -------------------------------------------------
    #  Private helpers
    # -------------------------------------------------
    def _scan_fast_briefly(self) -> None:
        """Scan fast for a short time to find new peers."""
        self._ble.gap_scan(_FAST_CONNECT_MS, _FAST_SCAN_INT_US, _FAST_SCAN_WIN_US)

    def _scan_slow_forever(self) -> None:
        """Scan slow to find new peers."""
        self._ble.gap_scan(0, _SLOW_SCAN_INT_US, _SLOW_SCAN_WIN_US)

    # -------------------------------------------------
    #  Public helpers
    # -------------------------------------------------
    def send(self, conn_handle: int, msg: bytes) -> None:
        """Write a command to a single ESP32 (does NOT await a response)."""
        peer = self._peers.get(conn_handle)
        if not peer or peer.tx_handle is None:
            return
        # write with response (1) to the tx_handle
        self._ble.gattc_write(conn_handle, peer.tx_handle, msg, 1)  # type: ignore[reportArgumentType]

    def broadcast(self, msg: bytes) -> None:
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
            and _VOTE_SVC_UUID_BIN in bytes(adv_data)
            and addr not in self._peer_addrs
        ):
            # Stop scanning momentarily to init
            self._connecting = True
            self._ble.gap_scan(None)  # type: ignore[reportArgumentType] stop scanning
            self._ble.gap_connect(addr_type, addr)  # Non-blocking
            print("Connecting to", self._addr_hex(addr))

    def _handle_scan_done(self) -> None:
        if not self._connecting:
            self._scan_slow_forever()

    def _handle_peripheral_connect(self, data: tuple) -> None:
        conn_handle, addr_type, addr = data
        peer = _Peer(bytes(addr))
        peer.conn_handle = conn_handle
        self._peers[conn_handle] = peer
        self._peer_addrs.append(bytes(addr))
        print("Connected", conn_handle)
        # Discover Vote service
        self._ble.gattc_discover_services(conn_handle)

    def _handle_gattc_service_result(self, data: tuple) -> None:
        conn_handle, start_handle, end_handle, uuid = data
        if uuid == VOTE_SVC_UUID:
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
        if uuid == VOTE_NOTIFY_CHAR_UUID:
            peer.rx_handle = value_handle
        elif uuid == VOTE_WRITE_CHAR_UUID:
            peer.tx_handle = value_handle

    def _handle_gattc_characteristic_done(self, data: tuple) -> None:
        conn_handle, status = data
        peer = self._peers.get(conn_handle)
        if not peer or status != 0 or peer.rx_handle is None:
            return
        # Enable notifications: write 0x0001 to CCCD (rx_handle + 1)
        cccd = peer.rx_handle + 1  # type: ignore[reportOperatorIssue]
        self._ble.gattc_write(conn_handle, cccd, _ENABLE_NOTIFY, 1)
        print("Subscribed to", conn_handle)
        # Resume scanning if we need more peers
        self._connecting = False
        if len(self._peers) < self._max_peers:
            self._scan_fast_briefly()

    def _handle_gattc_notify(self, data: tuple) -> None:
        conn_handle, value_handle, notify_data = data
        if self._on_rx:
            self._on_rx(conn_handle, bytes(notify_data))

    def _handle_peripheral_disconnect(self, data: tuple) -> None:
        conn_handle, addr_type, addr = data
        print("Disconnected", conn_handle)
        peer = self._peers.pop(conn_handle, None)
        if peer is not None:
            try:
                self._peer_addrs.remove(peer.addr)
            except ValueError:
                pass
        # Scan again to replace the lost link
        self._connecting = False
        self._scan_fast_briefly()

    def _irq(self, event: int, data: tuple) -> None:
        if event == _IRQ_SCAN_RESULT:
            self._handle_scan_result(data)
        elif event == _IRQ_SCAN_DONE:
            self._handle_scan_done()
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
