"""Download latin WOFF2 files from Google Fonts and generate a local fonts.css.

Run once from repo root: python scripts/fetch-fonts.py
Outputs:
  - app/static/fonts/*.woff2  (committed)
  - app/static/css/fonts.css  (committed)
"""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

GFONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Instrument+Serif:ital@0;1"
    "&family=IBM+Plex+Sans:ital,wght@0,400;0,500;1,400"
    "&family=IBM+Plex+Mono:wght@400"
    "&display=swap"
)
MODERN_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / "app" / "static" / "fonts"
CSS_OUT = ROOT / "app" / "static" / "css" / "fonts.css"


def http_get(url: str, binary: bool = False) -> bytes | str:
    req = urllib.request.Request(url, headers={"User-Agent": MODERN_UA})
    data = urllib.request.urlopen(req).read()
    return data if binary else data.decode()


def slugify(family: str, style: str, weight: str) -> str:
    fam = family.lower().replace(" ", "-")
    return f"{fam}-{weight}{'-italic' if style == 'italic' else ''}.woff2"


def main() -> None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    css = http_get(GFONTS_URL)

    # Split into labeled blocks: /* subset */ @font-face {...}
    parts = re.split(r"/\*\s*([\w-]+)\s*\*/", css)
    faces: list[str] = []
    for i in range(1, len(parts), 2):
        if parts[i] == "latin":
            faces.append(parts[i + 1])

    out_css_lines = [
        "/* Self-hosted Google Fonts (latin subset, WOFF2, font-display: swap). */",
        "/* Regenerate with: python scripts/fetch-fonts.py                     */",
        "",
    ]

    for block in faces:
        family = re.search(r"font-family:\s*'([^']+)'", block).group(1)
        style = re.search(r"font-style:\s*(\w+)", block).group(1)
        weight = re.search(r"font-weight:\s*(\d+)", block).group(1)
        url = re.search(r"url\((https://[^)]+\.woff2)\)", block).group(1)
        unicode_range = re.search(r"unicode-range:\s*([^;]+);", block)

        filename = slugify(family, style, weight)
        target = FONTS_DIR / filename

        print(f"  {family} {style} {weight} -> {filename}")
        target.write_bytes(http_get(url, binary=True))

        out_css_lines.append("@font-face {")
        out_css_lines.append(f"  font-family: '{family}';")
        out_css_lines.append(f"  font-style: {style};")
        out_css_lines.append(f"  font-weight: {weight};")
        out_css_lines.append("  font-display: swap;")
        out_css_lines.append(f"  src: url('/static/fonts/{filename}') format('woff2');")
        if unicode_range:
            out_css_lines.append(f"  unicode-range: {unicode_range.group(1).strip()};")
        out_css_lines.append("}")
        out_css_lines.append("")

    CSS_OUT.write_text("\n".join(out_css_lines), encoding="utf-8")
    print(f"\nWrote {CSS_OUT.relative_to(ROOT)}")
    print(f"Wrote {len(faces)} fonts to {FONTS_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
