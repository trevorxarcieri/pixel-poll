# Pixel Poll

An embedded game night voting system project for my computer engineering capstone class. The project involves multiple voting controllers and one central module, where the central module is used to facilitate a vote and people can use their voting controllers to cast a vote.

## Repo Structure

```text
/
├── cmd/                       # TinyGo & host executables (one sub‑dir per main)
│   ├── central/               # TinyGo main() for the Raspberry Pi Pico 2 W
│   └── controller_demo/       # Host‑only Go stub that mimics an ESP32 controller
│
├── firmware/                  # Low‑level C/C++ source that runs directly on MCUs
│   ├── pico/                  # RP2040 drivers, ISRs, linker script, CMakeLists.txt
│   └── esp32/                 # Full ESP‑IDF project for each ESP32‑C3 controller
│
├── pkg/                       # Re‑usable, hardware‑agnostic libraries
│   ├── protocol/              # Wire‑format schema + generated Go/C/Python code
│   ├── central/               # Pure‑Go business logic for the central node
│   └── controller/            # Logic shared (or ported) to the ESP32 firmware
│
├── hal/                       # Hardware‑abstraction layers behind clean interfaces
│   ├── mock/                  # Fake peripherals for unit & sim tests
│   ├── pico/                  # TinyGo ↔ C shims binding Pico drivers
│   └── esp32/                 # Thin C wrappers around ESP‑IDF peripherals
│
├── tests/                     # All automated verification
│   ├── unit/                  # Pure logic tests (fast, no I/O)
│   │   ├── go/
│   │   ├── c/
│   │   └── py/
│   ├── sim/                   # End‑to‑end tests that run entirely on a laptop
│   │   ├── fixtures/          # Shared PyTest fixtures (MemoryTransport, FakeBLE…)
│   │   └── host/              # Tests that spin up host‑built central + stub controllers
│   └── hil/                   # Hardware‑in‑the‑loop tests on real boards
│       ├── pico/
│       ├── esp32/
│       └── system/
│
├── tools/                     # Helper scripts (flash, log capture, generators)
│
├── docs/                      # Architecture diagrams, GATT tables, reference PDFs
│
└── .github/
    └── workflows/             # CI/CD pipelines for lint, build, test, release
```
