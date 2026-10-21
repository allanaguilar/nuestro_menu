#!/usr/bin/env python3
"""Genera iconos PWA PNG sin dependencias externas."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path


def png(size: int, rgb=(92, 107, 74)) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            margin = size // 8
            inside = margin <= x < size - margin and margin <= y < size - margin
            color = rgb if inside else (246, 241, 232)
            raw.extend(color)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)),
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
            chunk(b"IEND", b""),
        ]
    )


def main() -> None:
    dest = Path(__file__).resolve().parent.parent / "static" / "icons"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "icon-192.png").write_bytes(png(192))
    (dest / "icon-512.png").write_bytes(png(512))


if __name__ == "__main__":
    main()
