"""Run this once to create a placeholder toishi.ico if it does not exist."""
import struct
from pathlib import Path


def make_ico() -> bytes:
    w, h = 16, 16
    bpp = 32
    pixel_data = b"\xd3\x1b\x1b\xff" * (w * h)
    and_mask = b"\x00" * (h * ((w + 31) // 32) * 4)
    bi = struct.pack(
        "<IiiHHIIiiII",
        40, w, h * 2, 1, bpp, 0,
        len(pixel_data) + len(and_mask),
        0, 0, 0, 0,
    )
    img_data = bi + pixel_data + and_mask
    ico_header = struct.pack("<HHH", 0, 1, 1)
    dir_entry = struct.pack("<BBBBHHII", w, h, 0, 0, 1, bpp, len(img_data), 6 + 16)
    return ico_header + dir_entry + img_data


if __name__ == "__main__":
    dest = Path(__file__).parent / "toishi" / "assets" / "toishi.ico"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(make_ico())
        print(f"Created {dest}")
    else:
        print(f"Already exists: {dest}")
