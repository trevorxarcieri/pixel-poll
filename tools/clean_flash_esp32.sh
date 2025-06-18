#!/bin/bash
# This script is used to flash the ESP32 with firmware and our software.
# It must be run from the root of the repository.

source venvs/esp32/bin/activate
esptool.py erase_flash
sleep 3
esptool.py --baud 460800 write_flash 0 firmware/ESP32_GENERIC_C3-20250415-v1.25.0.bin
sleep 3
mpremote fs cp -r src/controller/. :
deactivate
echo "ESP32 ls output:"
mpremote fs ls