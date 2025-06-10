import machine
from ble_vote_manager import BleVoteManager

led = machine.Pin("LED", machine.Pin.OUT)  # onboard LED = GP25


def got_vote(node_id: int, payload: bytes) -> None:
    """Callback function to handle received votes."""
    print("Node", node_id, "sent", payload)
    led.toggle()


vc = BleVoteManager(on_rx=got_vote, max_peers=5)
vc.auto_connect()  # start scanning/connecting in background

while True:
    pass
