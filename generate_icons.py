#!/usr/bin/env python3

# Skript zur Generierung von Icon-Varianten aus einer Inkscape-SVG-Datei
# Autor: Tobias Kiertscher <dev@mastersign.de>
# Version: 2025-07-03
# Copyright: MIT License

# Abhängigkeiten:
#   - Python >= 3.8
#   - Inkscape
#   - ImageMagick

from pathlib import Path
from shutil import copy
from subprocess import run
import json
import xml.etree.ElementTree as XML

project_root = Path(__file__).parent

inkscape_executable = "inkscape"
imagemagick_executable = "magick"

tmp_dir = project_root / "tmp"
out_dir = project_root / "out"

config_file = project_root / "config.json"

svg_file = project_root / "template.svg"

NS_SVG = "http://www.w3.org/2000/svg"
NS_INKSCAPE = "http://www.inkscape.org/namespaces/inkscape"
NS = {
    "svg": NS_SVG,
    "inkscape": NS_INKSCAPE,
}


def svg_layers(svg: XML.ElementTree) -> set[str]:
    """
    Sucht alle SVG-Gruppen-Tags, die als Inkscape-Ebene gekennzeichnet sind,
    und gibt deren IDs zurück.
    """
    layers = svg.findall(".//svg:g[@inkscape:groupmode='layer']", NS)
    return set(l.attrib["id"] for l in layers)


def build_layer_style(all_layers: set[str], include_layers: set[str]) -> str:
    """
    Setzt einen CSS-Text für das Ein- und Ausblenden von Ebenen zusammen.
    """
    include_layer_style = "\n".join(
        f"#{id} {{ display: inline !important; }}" for id in include_layers)
    exclude_layers = all_layers - include_layers
    exclude_layer_style = "\n".join(
        f"#{id} {{ display: none !important; }}" for id in exclude_layers)
    return "\n".join([include_layer_style, exclude_layer_style])


def update_svg_style(svg: XML.ElementTree, style: str, id: str = "icondev"):
    """
    Aktualisiert den Text eines style-Tags in dem übergebenen SVG.
    Wenn kein style-Tag mit der gegebenen ID gefunden wird, wird es dem SVG hinzugefügt.
    """
    style_node = svg.find(f".//svg:style[@id='{id}']", NS)

    if style_node is None:
        style_node = XML.SubElement(svg.getroot(), XML.QName(NS_SVG, "style").text)
        style_node.set("id", id)

    style_node.text = style


def run_command(command: list[str], exit_on_error: bool = True):
    """
    Führt ein Befehlszeilenprogramm aus.
    Gibt im Fehlerfall die Standardfehlerausgabe aus.
    """
    result = run(command, capture_output=True)
    if result.returncode > 0 or result.stderr:
        print(result.stderr.decode(errors="replace"))
        if exit_on_error:
            exit(1)
        else:
            return False
    return True


def raster_command(src_svg_file: Path, size: int, target_png_file: Path) -> list[str]:
    return [
        inkscape_executable,
        f"--export-width={size}",
        f"--export-filename={target_png_file}",
        str(src_svg_file),
    ]


def sharpen_command(file: Path, sharpen: float):
    return [
        imagemagick_executable,
        "convert",
        str(file),
        "-sharpen",
        f"0x{sharpen}",
        str(file),
    ]


def ico_command(src_dir: Path, target_dir: Path, sizes: list[int], name: str) -> list[str]:
    return [
        imagemagick_executable,
        "convert",
        *(str(src_dir / f"{s}.png") for s in sizes),
        str(target_dir / f"{name}.ico"),
    ]


def generate_bitmaps(
        svg: XML.ElementTree,
        work_dir: Path,
        resolutions: list[dict],
        sharpen: float | None,
        clean: bool = False):
    """
    Rastert ein SVG in verschiedenen Auflösungen mit ausgewählten Ebenen.
    """

    if clean:
        # Temporäres Verzeichnis bereinigen
        for f in work_dir.glob("*"):
            f.unlink()

    # Inkscape-Ebenen ermitteln
    all_layers = svg_layers(svg)

    # Auflösungen abarbeiten
    for res in resolutions:
        include_layers = set(res["layers"])

        # SVG vorbereiten
        layer_style = build_layer_style(all_layers, include_layers)
        update_svg_style(svg, layer_style, id="layer-visibility")
        tmp_svg_file = work_dir / "styled.svg"
        svg.write(str(tmp_svg_file))

        # SVG in verschiedenen Bildgrößen rastern
        sizes = res["sizes"]
        for size in sizes:
            filename = work_dir / f"{size}.png"
            if filename.exists():
                continue
            print("Bitmap mit", size, "Pixeln Kantenlänge rastern. Ebenen:",
                  ", ".join(include_layers))
            run_command(raster_command(tmp_svg_file, size, filename))
            # Bei Bedarf Bitmap nachschärfen
            if sharpen is not None and sharpen > 0.0:
                run_command(sharpen_command(filename, sharpen))


def copy_png_files(work_dir: Path, target_dir: Path, png_files: dict):
    """
    Kopiert PNG-Dateien unter neuem Namen in das Ausgabeverzeichnis.
    """
    for name, size in png_files.items():
        print("PNG:", name)
        copy(work_dir / f"{size}.png", target_dir / f"{name}.png")


def build_ico_files(work_dir: Path, target_dir: Path, ico_files: dict):
    """
    Erzeugt ICO-Dateien aus mehreren PNG-Dateien.
    """
    for name, sizes in ico_files.items():
        print("ICO:", name)
        run_command(ico_command(work_dir, target_dir, sizes, name))


if __name__ == "__main__":
    # Hauptprogramm

    # Verzeichnisse vorbereiten
    tmp_dir.mkdir(exist_ok=True)
    out_dir.mkdir(exist_ok=True)

    # Konfiguration einlesen
    with open(config_file, "rb") as f:
        config = json.load(f)

    resolutions = config["resolutions"]
    png_files = config["png_files"]
    ico_files = config["ico_files"]
    sharpen = config["sharpen"]

    # SVG laden
    svg = XML.parse(str(svg_file))

    # Bitmaps rastern, schärfen und im Ausgabeverzeichnis ablegen
    generate_bitmaps(svg, tmp_dir, resolutions, sharpen, clean=True)
    copy_png_files(tmp_dir, out_dir, png_files)
    build_ico_files(tmp_dir, out_dir, ico_files)
