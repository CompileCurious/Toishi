"""Create placeholder ICO assets for the Toishi project.

Generates a multi-size ICO (16, 32, 48, 128) so Windows Explorer and the
taskbar can each pick an appropriate resolution, avoiding the blue-square
fallback that occurs when only one size is present.
"""
import struct
from pathlib import Path

# Solid brand colour in BGRA: B=0x1b G=0x1b R=0xd3 A=0xff (dark-red)
_COLOUR = b"\x1b\x1b\xd3\xff"


def _bmp_entry(size: int) -> bytes:
    """Return a BITMAPINFOHEADER + pixel data + AND mask for one ICO frame."""
    pixel_data = _COLOUR * (size * size)
    row_bytes = ((size + 31) // 32) * 4          # AND-mask row stride (DWORD-aligned)
    and_mask = b"\x00" * (row_bytes * size)
    header = struct.pack(
        "<IiiHHIIiiII",
        40, size, size * 2, 1, 32, 0,
        len(pixel_data) + len(and_mask),
        0, 0, 0, 0,
    )
    return header + pixel_data + and_mask


def make_ico(sizes: tuple = (16, 32, 48, 128)) -> bytes:
    """Assemble a multi-size ICO file from BMP frames."""
    images = [_bmp_entry(s) for s in sizes]
    n = len(images)
    ico_header = struct.pack("<HHH", 0, 1, n)
    data_offset = 6 + n * 16
    dir_entries = b""
    for s, img in zip(sizes, images):
        w = s if s < 256 else 0
        h = s if s < 256 else 0
        dir_entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(img), data_offset)
        data_offset += len(img)
    return ico_header + dir_entries + b"".join(images)


if __name__ == "__main__":
    root = Path(__file__).parent
    ico_data = make_ico()

    # toishi/assets/toishi.ico  (bundled into the exe via the spec)
    assets_ico = root / "toishi" / "assets" / "toishi.ico"
    assets_ico.parent.mkdir(parents=True, exist_ok=True)
    assets_ico.write_bytes(ico_data)
    print(f"Created {assets_ico}")

    # Icon.ico at repo root  (embedded by PyInstaller as the exe icon)
    root_ico = root / "Icon.ico"
    root_ico.write_bytes(ico_data)
    print(f"Created {root_ico}")
