#!/usr/bin/env python3
"""Dev-only: rasterise the panels to PNG contact sheets for eyeballing.

Not used by CI and not required to build the profile — the shipped assets are
SVG. This exists so the art can be reviewed locally without depending on a
browser screenshot. Requires Pillow; everything else in scripts/ is stdlib.

    python scripts/preview_png.py
"""

import pathlib
import sys

from PIL import Image, ImageDraw

import art
import ghdata
import render_profile as rp

OUT = pathlib.Path(__file__).resolve().parent.parent / "_preview"
GAP = 12


def rasterise(canvas):
    s = canvas.scale
    img = Image.new("RGB", (canvas.w * s, canvas.h * s), "#ff00ff")
    d = ImageDraw.Draw(img)
    for x, y, w, h, color in canvas.ops:
        d.rectangle([x * s, y * s, (x + w) * s - 1, (y + h) * s - 1], fill=color)
    return img


def fake_calendar(data):
    """Synthetic contributions, so the populated garden can be reviewed locally.

    The garden needs a token, which only CI has, so without this the busy state
    would ship having never been looked at. Preview only — never written to the
    committed SVGs, which always render whatever the API actually returned.
    """
    weeks = []
    for w in range(53):
        week = []
        for d in range(7):
            n = (w * 7 + d)
            week.append(max(0, (n * 7919 % 11) - 4 + (3 if w > 40 else 0)))
        weeks.append(week)
    data = dict(data)
    data["calendar"] = weeks
    data["total_contributions"] = sum(sum(w) for w in weeks)
    return data


def main():
    OUT.mkdir(exist_ok=True)
    data = ghdata.fetch(rp.USER)
    if "--demo-garden" in sys.argv:
        data = fake_calendar(data)
        print("!! demo garden: contribution data below is FAKE, preview only")
    for theme in art.THEMES:
        panels = []
        for name, fn in rp.PANELS.items():
            # Re-run each draw fn against a fresh canvas to collect its ops.
            canvas = _capture(fn, data, theme)
            panels.append(rasterise(canvas))
        width = max(p.width for p in panels)
        height = sum(p.height for p in panels) + GAP * (len(panels) + 1)
        bg = "#0d1117" if theme["name"] == "dark" else "#ffffff"
        sheet = Image.new("RGB", (width + GAP * 2, height), bg)
        y = GAP
        for p in panels:
            sheet.paste(p, (GAP, y))
            y += p.height + GAP
        path = OUT / f"sheet-{theme['name']}.png"
        sheet.save(path)
        print(f"wrote {path}  ({sheet.width}x{sheet.height})")


def _capture(fn, data, theme):
    """Call a draw_* fn but keep the Canvas instead of the SVG string."""
    captured = []
    real_svg = art.Canvas.svg

    def spy(self, title=""):
        captured.append(self)
        return real_svg(self, title)

    art.Canvas.svg = spy
    try:
        fn(data, theme)
    finally:
        art.Canvas.svg = real_svg
    return captured[-1]


if __name__ == "__main__":
    sys.exit(main())
