#!/usr/bin/env python3
"""Genera iconos PWA PNG a partir de static/icons/app-icon-source.jpg."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    dest = Path(__file__).resolve().parent.parent / "static" / "icons"
    source = dest / "app-icon-source.jpg"
    if not source.exists():
        raise SystemExit(f"Falta {source.name}.")
    sizes = {
        "icon-192.png": 192,
        "icon-512.png": 512,
        "apple-touch-icon.png": 180,
    }
    for name, size in sizes.items():
        subprocess.run(
            [
                "sips",
                "-s",
                "format",
                "png",
                "-z",
                str(size),
                str(size),
                str(source),
                "--out",
                str(dest / name),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    print("Iconos actualizados:", ", ".join(sizes))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError:
        sys.exit(1)
