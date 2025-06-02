# Pixel Poll

An embedded game night voting system project for my computer engineering capstone class. The project involves multiple voting controllers and one central module, where the central module is used to facilitate a vote and people can use their voting controllers to cast a vote.

## Repo Structure

```text
pixel-poll/                        # project root - hold pyproject.toml, README, lint configs
├── src/                           # MicroPython runtime code that will be copied to boards
│   ├── common/                    # Protocols, helpers, & logic shared by all MCUs
│   ├── central/                   # Application code for the RP2350-Pico W “central” unit
│   └── controller/                # Application code for the ESP32-C3 voting controllers
│
├── tests/                         # Host-side Pytest suites (run under mocked MicroPython)
│   ├── rp2/                       # Tests executed with RP2350 (rp2) stubs loaded
│   │   ├── unit/                  # Fast, pure-logic tests (no I/O, no transport)
│   │   ├── sim/                   # End-to-end vote-flow tests using fake transports
│   │   └── hil/                   # Hardware-in-the-loop tests flashing a real Pico W
│   │
│   └── esp32/                     # Tests executed with ESP32-C3 stubs loaded
│       ├── unit/                  # Pure-logic controller tests
│       ├── sim/                   # Simulated end-to-end controller tests
│       └── hil/                   # Hardware-in-the-loop tests flashing a real ESP32-C3
│
├── venvs/                         # Local poetry virtual-envs (ignored by Git)
│   ├── rp2/                       # Environment with dev + rp2 dependencies installed
│   └── esp32/                     # Environment with dev + esp32 dependencies installed
│
├── tools/                         # Helper scripts for flashing, packing FS images, mocks
│
├── docs/                          # Architecture diagrams, requirements, design notes
│
└── .github/
    └── workflows/                 # CI pipelines: lint -> rp2 tests -> esp32 tests -> artifacts
```

## Development Setup

### Prerequisites

- [Python](https://www.python.org/downloads/) 3.12 or later
- [Poetry](https://python-poetry.org/docs/) for Python package management

### Installing Dependencies

#### Install the Project

To install the project and its dependencies, run:

```bash
poetry install
```

#### RP2350 Virtual Environment

To install the required Python dependencies of the RP2350, run:

```bash
python -m venv venvs/rp2
source venvs/rp2/bin/activate
poetry install --only micropython,esp32
```

#### ESP32-C3 Virtual Environment

To install the required Python dependencies of the ESP32, run:

```bash
python -m venv venvs/esp32
source venvs/esp32/bin/activate
poetry install --only micropython,esp32
```

#### Updating Dependencies

When updating dependencies, you should do so using `poetry` commands on the root poetry virtual environment, *not* in the individual board environments. After doing so, you should run the following commands for each board to update the board-specific virtual environments:

```bash
source venvs/<board>/bin/activate
poetry sync --with <board>
```

## Flashing MicroPython Firmware

### Raspberry Pi Pico 2 W Firmware

Hold down the BOOTSEL button while plugging the board into USB. The UF2 file from the below page should then be copied to the USB mass storage device that appears.
See the [firmware download page](https://micropython.org/download/RPI_PICO2_W/) for more details.

### ESP32-C3 Firmware

```bash
source venvs/esp32/bin/activate
esptool.py erase_flash
esptool.py --baud 460800 write_flash 0 ESP32_BOARD_NAME-DATE-VERSION.bin
```

See the [firmware download page](https://micropython.org/download/ESP32_GENERIC_C3/) for more details.

## MicroPython Software

### Flashing Software

To flash software to a board, connect the board to your computer via USB and use the following commands:

```bash
source venvs/<board>/bin/activate
mpremote connect auto
mpremote fs cp host_script.py :board_script.py
mpremote disconnect
```

The `host_script.py` is the script you want to run on the board, and `board_script.py` is the name it will have on the board. Micropython automatically runs `boot.py` followed by `main.py` on boot, so you can files with these names will run automatically.

### Running Software

To run a script from your host machine on the board, you can use:

```bash
source venvs/<board>/bin/activate
mpremote connect auto
mpremote run board_script.py
mpremote disconnect
```
