# Simple BLE battery-level peripheral (always 100 %)
# Works on MicroPython v1.20+  (ESP32, RP2040-W, nRF boards)

import struct
import time

import bluetooth
from micropython import const

# IRQ event codes
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)

# Standard Battery Service & Characteristic UUIDs
UUID_BATTERY_SERVICE = bluetooth.UUID(0x180F)  # Battery Service
UUID_BATTERY_LEVEL = bluetooth.UUID(0x2A19)  # Battery Level (%)

# Advertised battery value
BATTERY_LEVEL = 0x45

# Build a single-service GATT containing one readable/notifiable characteristic
battery_level_char = (
    UUID_BATTERY_LEVEL,
    bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,
)
BATTERY_SERVICE = (UUID_BATTERY_SERVICE, (battery_level_char,))

ble = bluetooth.BLE()
ble.active(True)
# Register the service and get the handle of the characteristic
((handle_batt_level,),) = ble.gatts_register_services((BATTERY_SERVICE,))

# Write the initial value (one unsigned byte, 0–100)
ble.gatts_write(handle_batt_level, struct.pack("B", BATTERY_LEVEL))


def advertising_payload(name: bytes, services=None) -> bytearray:
    """Create an advertising payload with the device name and service UUIDs."""
    payload = bytearray()

    def _append(ad_type, value):
        payload.extend(struct.pack("BB", len(value) + 1, ad_type) + value)

    # Flags: general-discoverable, BR/EDR unsupported
    _append(0x01, struct.pack("B", 0x06))
    _append(0x09, name)  # Complete Local Name

    if services:
        for uuid in services:
            b = bytes(uuid)
            _append(0x03 if len(b) == 2 else 0x07, b)

    return payload


def _irq(event, data):
    """Notify the battery level when a central connects and restart advertising when it disconnects."""
    if event == _IRQ_CENTRAL_CONNECT:
        conn_handle, *_ = data
        # Give the central a moment to discover services
        time.sleep_ms(200)
        ble.gatts_notify(handle_batt_level, struct.pack("B", BATTERY_LEVEL))

    elif event == _IRQ_CENTRAL_DISCONNECT:
        # Restart advertising so another device can connect
        advertise()


ble.irq(_irq)


def advertise(interval_us=500_000):
    """Start BLE advertising with a given interval."""
    name = b"MicroPyBatt"
    ble.gap_advertise(interval_us, advertising_payload(name, [UUID_BATTERY_SERVICE]))
    print("Advertising as", name.decode())


advertise()
