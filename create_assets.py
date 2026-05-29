"""Prepare ICO assets for the Toishi project.

- toishi/assets/toishi.ico : placeholder, always regenerated (used at runtime).
- Icon.ico                 : expanded in-place to include 16/32/48/128 px frames
                             so PyInstaller embeds a proper Windows PE icon group
                             and the exe shows the correct icon in Explorer.
                             Only touched when Pillow is available; left alone
                             otherwise so a manual/custom icon is never destroyed.
"""
import struct
from pathlib import Path

try:
    from PIL import Image
    _HAVE_PILLOW = True
except ImportError:
    _HAVE_PILLOW = False

# Solid brand colour in BGRA for the placeholder: B=0x1b G=0x1b R=0xd3 A=0xff
_COLOUR = b"\x1b\x1b\xd3\xff"
_ICO_SIZES = [16, 32, 48, 128]


# ---------------------------------------------------------------------------
# Pure-Python placeholder builder (no dependencies)
# ---------------------------------------------------------------------------

def _bmp_entry(size: int) -> bytes:
    """BITMAPINFOHEADER + pixel data + AND mask for one ICO frame."""
    pixel_data = _COLOUR * (size * size)
    row_bytes = ((size + 31) // 32) * 4
    and_mask = b"\x00" * (row_bytes * size)
    header = struct.pack(
        "<IiiHHIIiiII",
        40, size, size * 2, 1, 32, 0,
        len(pixel_data) + len(and_mask),
        0, 0, 0, 0,
    )
    return header + pixel_data + and_mask


def _make_placeholder_ico() -> bytes:
    images = [_bmp_entry(s) for s in _ICO_SIZES]
    n = len(images)
    ico_header = struct.pack("<HHH", 0, 1, n)
    data_offset = 6 + n * 16
    entries = b""
    for s, img in zip(_ICO_SIZES, images):
        w = s if s < 256 else 0
        entries += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(img), data_offset)
        data_offset += len(img)
    return ico_header + entries + b"".join(images)


# ---------------------------------------------------------------------------
# Pillow-based multi-size expander
# ---------------------------------------------------------------------------

def _expand_ico_with_pillow(src: Path, dest: Path) -> None:
    """Re-save *src* as a multi-size ICO at *dest* using Pillow."""
    img = Image.open(src).convert("RGBA")
    sizes = [(s, s) for s in _ICO_SIZES]
    img.save(dest, format="ICO", sizes=sizes)
    print(f"Expanded {dest} → sizes {_ICO_SIZES}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = Path(__file__).parent

    # 1. toishi/assets/toishi.ico — placeholder, always written fresh
    assets_ico = root / "toishi" / "assets" / "toishi.ico"
    assets_ico.parent.mkdir(parents=True, exist_ok=True)
    assets_ico.write_bytes(_make_placeholder_ico())
    print(f"Created {assets_ico}")

    # 2. Icon.ico — expand to multi-size using Pillow so the exe icon works
    root_ico = root / "Icon.ico"
    if root_ico.exists() and _HAVE_PILLOW:
        _expand_ico_with_pillow(root_ico, root_ico)
    elif not root_ico.exists():
        root_ico.write_bytes(_make_placeholder_ico())
        print(f"Created placeholder {root_ico}")
    else:
        print("Pillow not installed — Icon.ico left unchanged (run: pip install pillow)")
