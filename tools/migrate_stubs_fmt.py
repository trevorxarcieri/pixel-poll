"""Migrate the format of all stubs in the virtual environments."""

from pathlib import Path

VENVS_DIR = Path(__file__).parent.parent / "venvs"
ESP32_DIR = VENVS_DIR / "esp32" / "lib" / "python3.12" / "site-packages"
RP2_DIR = VENVS_DIR / "rp2" / "lib" / "python3.12" / "site-packages"


def migrate_stubs(name: str, path: Path) -> None:
    """Migrate the stubs format for a given virtual environment.

    Args:
        name: The name of the virtual environment.
        path: The path to the virtual environment.
    """
    print(f"Migrating stubs for {name}...")
    migrated_stubs = []
    for file in path.glob("*.pyi"):
        if isinstance(file, Path) and file.is_file() and not file.name.startswith("__"):
            Path(file.parent / file.stem).mkdir(parents=True)
            file.rename(file.parent / file.stem / "__init__.pyi")
            migrated_stubs.append(file.stem)

    print(f"Finished migrating stubs for {name}: {migrated_stubs}")


def main():
    """Main function to migrate stubs format.

    This script will look for all stub (modulename.pyi) files in the virtual environments'
    site-packages directory and change them to modulename/__init__.pyi.
    """
    migrate_stubs("esp32", ESP32_DIR)
    migrate_stubs("rp2", RP2_DIR)
