import time

import machine
import micropython
from ble_vote_manager import BleVoteManager

micropython.alloc_emergency_exception_buf(100)

led = machine.Pin("LED", machine.Pin.OUT)  # onboard LED = GP25


def got_vote(node_id: int, payload: bytes) -> None:
    """Callback function to handle received votes."""
    print("Node", node_id, "sent", payload.decode('utf-8'))
    led.toggle()


vm = BleVoteManager(on_rx=got_vote, max_peers=5)

while True:
    vm.broadcast(b"HI")
    print("sent HI")
    time.sleep(5)  # broadcast every 5 seconds
