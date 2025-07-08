#!/usr/bin/env python3

# Skript zur Generierung einer Übersicht aus mehreren Auflösungsvarianten eines Icons.
# Autor: Tobias Kiertscher <dev@mastersign.de>
# Version: 2025-07-08
# Copyright: MIT License

# Abhängigkeiten:
#   - Python >= 3.8
#   - ImageMagick

from pathlib import Path
from subprocess import run
import json
import sys

project_root = Path(__file__).parent

imagemagick_executable = "magick"

tmp_dir = project_root / "tmp"
out_dir = project_root / "out"

config_file = project_root / "config.json"

font = "Segoe-UI"


def run_command(command: list[str], exit_on_error: bool = True, working_dir: Path | None = None):
    """
    Führt ein Befehlszeilenprogramm aus.
    Gibt im Fehlerfall die Standardfehlerausgabe aus.
    """
    result = run(command, capture_output=True, cwd=working_dir)
    if result.returncode > 0 or result.stderr:
        if result.stderr:
            print(result.stderr.decode(errors="replace"), file=sys.stderr)
        if exit_on_error:
            exit(1)
        else:
            return False
    return True


def tile_command(size: int, max_size: int):
    w = size + 12
    h = max_size + 32
    return [
        imagemagick_executable,
        "-size", f"{w}x{h}",
        "canvas:transparent",
        "-gravity", "South",
        "-draw", f"image over 0,32 {size},{size} '{size}.png'",
        "-fill", "#FFFFFFAA", "-stroke", "none",
        "-draw", f"rectangle 0,{h - 22} {w},{h}",
        "-fill", "black",
        "-font", font, "-pointsize", "12",
        "-draw", f"text 0,4 '{size}px'",
        f"{size}_tile.png",
    ]


def concat_command(target_file: Path, tmp_dir: Path, sizes: list[int]) -> list[str]:
    return [
        imagemagick_executable,
        "montage",
        "-background", "transparent",
        *(str(tmp_dir / f"{s}_tile.png") for s in sizes),
        "-mode", "Concatenate",
        "-tile", "x1",
        "-geometry", "+4+0",
        str(target_file),
    ]


def generate_overview(tmp_dir: Path, out_dir: Path, sizes: list[int]):
    """
    Erzeugt eine Übersicht des Icons in mehreren Auflösungen.
    """
    # Kacheln erzeugen
    for size in sizes:
        run_command(tile_command(size, max(*sizes)), working_dir=tmp_dir)
    # Übersicht zusammensetzen
    run_command(concat_command(out_dir / "overview.png", tmp_dir, sizes))
    # Kacheln löschen
    for f in tmp_dir.glob("*_tile.png"):
        f.unlink()


if __name__ == "__main__":
    # Hauptprogramm

    # Verzeichnisse vorbereiten
    if not tmp_dir.exists():
        print("Arbeitsverzeichnis wurde nicht gefunden.", file=sys.stderr)
        exit(1)

    out_dir.mkdir(exist_ok=True)

    # Konfiguration einlesen
    with open(config_file, "rb") as f:
        config = json.load(f)

    sizes = config["overview_resolutions"]

    # Übersichtsgrafik für verschiedene Auflösungen erzeugen
    generate_overview(tmp_dir, out_dir, sizes)
