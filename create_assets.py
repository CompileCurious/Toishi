"""Prepare ICO assets for the Toishi project.

- toishi/assets/toishi.ico  : placeholder, always regenerated (satisfies the
                              spec datas entry; not used directly by the app).
- toishi/assets/Icon_win.ico: multi-size ICO (16/32/48/128 px) derived from
                              Icon.ico and used ONLY as the PyInstaller PE icon
                              so Windows Explorer shows the correct exe icon.
                              Icon.ico itself is NEVER modified so pywebview
                              (GUI window + system tray) always gets the
                              original file it expects.
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
# Pillow-based multi-size builder
# ---------------------------------------------------------------------------

def _make_win_ico(src: Path, dest: Path) -> None:
    """Save a multi-size ICO derived from *src* to *dest* using Pillow."""
    img = Image.open(src).convert("RGBA")
    sizes = [(s, s) for s in _ICO_SIZES]
    img.save(dest, format="ICO", sizes=sizes)
    print(f"Created {dest} (sizes: {_ICO_SIZES})")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = Path(__file__).parent
    assets_dir = root / "toishi" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 1. toishi/assets/toishi.ico -- placeholder (required by spec datas)
    assets_ico = assets_dir / "toishi.ico"
    assets_ico.write_bytes(_make_placeholder_ico())
    print(f"Created {assets_ico}")

    # 2. toishi/assets/Icon_win.ico -- multi-size PE icon for PyInstaller
    #    Icon.ico is intentionally left untouched (used by pywebview at runtime)
    root_ico = root / "Icon.ico"
    win_ico = assets_dir / "Icon_win.ico"
    if root_ico.exists() and _HAVE_PILLOW:
        _make_win_ico(root_ico, win_ico)
    elif win_ico.exists():
        print(f"Pillow not installed -- keeping existing {win_ico}")
    else:
        win_ico.write_bytes(_make_placeholder_ico())
        print(f"Pillow not installed -- created placeholder {win_ico}")
