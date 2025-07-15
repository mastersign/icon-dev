#!/usr/bin/env python3

# Skript zur Generierung einer Übersicht aus mehreren Auflösungsvarianten eines Icons.
# Autor: Tobias Kiertscher <dev@mastersign.de>
# Version: 2025-07-08
# Copyright: MIT License

# Abhängigkeiten:
#   - Python >= 3.8
#   - ImageMagick

from os import getcwd
from pathlib import Path
from subprocess import run
import json
import sys

imagemagick_executable = "magick"
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


def concat_tiles_command(target_file: Path, tmp_dir: Path, sizes: list[int]) -> list[str]:
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


def concat_variants_command(target_file: Path, base_dir: Path, overview_file: str, variants: list[str]) -> list[str]:
    return [
        imagemagick_executable,
        "montage",
        "-background", "transparent",
        *(str(base_dir / v / overview_file) for v in variants),
        "-mode", "Concatenate",
        "-tile", "1x",
        "-geometry", "+0+4",
        str(target_file),
    ]


def generate_overview(tmp_dir: Path, out_dir: Path, result_file: str, sizes: list[int]):
    """
    Erzeugt eine Übersicht des Icons in mehreren Auflösungen.
    """
    # Kacheln erzeugen
    for size in sizes:
        run_command(tile_command(size, max(*sizes)), working_dir=tmp_dir)
    # Übersicht zusammensetzen
    run_command(concat_tiles_command(out_dir / result_file, tmp_dir, sizes))
    # Kacheln löschen
    for f in tmp_dir.glob("*_tile.png"):
        f.unlink()


def generate_variants_overview(tmp_dir: Path, out_dir: Path, result_file: str, sizes: list[int], variants: list[str]):
    """
    Erzeugt eine Übersicht des Icons in mehreren Auflösungen und Varianten.
    """
    # Übersicht für jede gegebene Variante erzeugen
    for variant in variants:
        variant_tmp_dir = tmp_dir / variant
        generate_overview(variant_tmp_dir, variant_tmp_dir, "overview.png", sizes)
    # Gesamtübersicht zusammensetzen
    run_command(concat_variants_command(out_dir / result_file, tmp_dir, "overview.png", variants))


def absolute_path(p: Path, base: Path):
    return p if p.is_absolute() else base / p


def assure_dir(p: Path, caption: str = "Verzeichnis"):
    """
    Prüft, ob das übergebene Verzeichnis existiert.
    Bricht das Programm mit Exit-Code 1 ab, falls das Verzeichnis nicht existiert.
    """
    if not p.exists() or not p.is_dir():
        print(caption, "wurde nicht gefunden.", file=sys.stderr)
        exit(1)
    return p


if __name__ == "__main__":
    # Hauptprogramm

    project_root = Path(getcwd())

    config_file = Path(sys.argv[1] if len(sys.argv) > 1 else "config.json")
    if not config_file.is_absolute():
        config_file = project_root / config_file

    # Konfiguration einlesen
    with open(config_file, "rb") as f:
        config = json.load(f)

    # Temporäres Verzeichnis überprüfen
    tmp_dir = absolute_path(Path(config["temp_dir"]), project_root)
    assure_dir(tmp_dir)
    # Ausgabeverzeichnis überprüfen
    out_dir = absolute_path(Path(config["output_dir"]), project_root)
    assure_dir(out_dir)

    # Konfiguration extrahieren
    sizes = config["overview_resolutions"]
    variants = config["overview_variants"]
    result_file = config["overview_file"]

    if len(variants) == 0:
        # Übersichtsgrafik für verschiedene Auflösungen erzeugen
        generate_overview(tmp_dir, out_dir, result_file, sizes)
    else:
        # Übersichtsgrafik für verschiedene Varianten und Auflösungen erzeugen
        generate_variants_overview(tmp_dir, out_dir, result_file, sizes, variants)
