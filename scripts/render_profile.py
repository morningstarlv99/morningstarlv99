#!/usr/bin/env python3
"""Renders the profile art from live GitHub data.

    python scripts/render_profile.py          # anonymous; garden stays empty
    GH_TOKEN=... python scripts/render_profile.py   # full render

Writes a light and a dark edition of every panel into assets/. The README
swaps between them with <picture media="(prefers-color-scheme: dark)">.

Nothing here is hand-maintained: add a repo, push a commit, earn a star, and
the next run redraws to match. That is the whole point of the rewrite.
"""

import pathlib
import sys

import art
import ghdata
import pixelfont as font
from art import Canvas

USER = "morningstarlv99"
ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

BANNER_TITLE = "MORNINGSTAR"
BANNER_DEK = "ONE PROBLEM, ONE PROOF, AT A TIME"
W = 220  # virtual canvas width shared by every panel


# --- banner -----------------------------------------------------------------

HORIZON = 72  # desk surface: everything below is foreground shadow
BANNER_H = 88


def draw_banner(data, theme):
    c = Canvas(W, BANNER_H)
    sky = theme["sky"]
    night = theme["name"] == "dark"

    # Sky, banded rather than gradient-filled: a gradient would betray the grid.
    for i, color in enumerate(sky):
        y0 = i * HORIZON // len(sky)
        y1 = (i + 1) * HORIZON // len(sky)
        c.px(0, y0, W, y1 - y0, color)

    # Stars at night, faint dawn specks by day. Fixed positions, not random:
    # the render must be deterministic or every run dirties the diff.
    specks = [(24, 5), (38, 12), (57, 4), (72, 16), (96, 7), (113, 3),
              (129, 14), (148, 6), (162, 19), (177, 4), (208, 26), (12, 22),
              (86, 24), (140, 27), (206, 44), (46, 44), (167, 48), (30, 52),
              (118, 50), (152, 41), (68, 47), (196, 54)]
    for i, (sx, sy) in enumerate(specks):
        color = theme["star"] if (night and i % 3 != 2) else theme["star_dim"]
        if night or i % 4 == 0:
            c.px(sx, sy, 1, 1, color)
            if night and i % 5 == 0:  # a few twinkle into little plus shapes
                c.px(sx - 1, sy, 1, 1, theme["star_dim"])
                c.px(sx + 1, sy, 1, 1, theme["star_dim"])
                c.px(sx, sy - 1, 1, 1, theme["star_dim"])
                c.px(sx, sy + 1, 1, 1, theme["star_dim"])

    # Moon by night, sun by dawn. Same circle, drawn as pixel rows.
    ocx, ocy, r = 190, 17, 9
    glow_rows = _disc_rows(r + 2)
    for dy, half in glow_rows:
        c.px(ocx - half, ocy + dy, half * 2 + 1, 1, theme["orb_glow"])
    for dy, half in _disc_rows(r):
        c.px(ocx - half, ocy + dy, half * 2 + 1, 1, theme["orb"])
    if night:  # craters
        c.px(ocx - 3, ocy - 3, 2, 2, theme["orb_shade"])
        c.px(ocx + 2, ocy + 1, 3, 2, theme["orb_shade"])
        c.px(ocx - 2, ocy + 4, 2, 1, theme["orb_shade"])
    else:
        # A low dawn sun: warm underside only. Anything more graphic than this
        # (rays, banding) stops reading as a sun and starts reading as an icon.
        for dy, half in _disc_rows(r):
            if dy >= 3:
                c.px(ocx - half, ocy + dy, half * 2 + 1, 1, theme["orb_shade"])

    # A couple of soft clouds, low and lazy.
    for cx0, cy0, cw in ((26, 44, 26), (124, 52, 30), (168, 38, 18)):
        c.px(cx0, cy0, cw, 2, theme["cloud"])
        c.px(cx0 + 3, cy0 - 1, cw - 8, 1, theme["cloud"])
        c.px(cx0 + 7, cy0 - 2, cw - 16, 1, theme["cloud"])

    # Rolling hills, far then near, meeting the horizon.
    _hill(c, 0, 60, W, theme["hill_far"], amp=4, period=61, phase=0, floor=HORIZON)
    _hill(c, 0, 65, W, theme["hill_near"], amp=3, period=43, phase=17, floor=HORIZON)

    # Title and dek, sitting in the sky.
    font.blit(c, BANNER_TITLE, 12, 10, theme["title"], scale=2)
    font.blit(c, BANNER_DEK, 12, 28, theme["subtitle"], scale=1)

    # Desk: everything below the horizon is foreground shadow, lit from behind
    # by the window. Sprites go in at 2x so they read as objects, not confetti.
    c.px(0, HORIZON, W, BANNER_H - HORIZON, theme["fg"])
    c.px(0, HORIZON, W, 1, theme["fg_edge"])

    pal = art.fg_palette(theme)
    for sprite, x, scale in (
        (art.PLANT, 12, 2),
        (art.MONITOR, 50, 2),
        (art.MUG, 106, 2),
        (art.CAT, 142, 2),
    ):
        sw, sh = Canvas.sprite_size(sprite, scale)
        assert x + sw <= W, f"sprite at x={x} overruns the {W}px canvas"
        c.sprite(sprite, x, HORIZON - sh, pal, scale)
    # Steam rises out of the mug, so it hangs above the mug's own top edge.
    _, mug_h = Canvas.sprite_size(art.MUG, 2)
    _, steam_h = Canvas.sprite_size(art.STEAM, 2)
    c.sprite(art.STEAM, 110, HORIZON - mug_h - steam_h, pal, 2)

    # Live caption along the desk edge.
    year = (data["created"] or "2026")[:4]
    caption_y = HORIZON + (BANNER_H - HORIZON - font.height(1)) // 2
    font.blit(c, f"EST. {year}", 8, caption_y, theme["muted"], scale=1)
    pushed = data["repos"][0]["pushed_at"] if data["repos"] else None
    stamp = f"LAST PUSH {ghdata.ago(pushed, data['generated'])}" if pushed else "NO PUSHES YET"
    font.blit_right(c, stamp, 212, caption_y, theme["muted"], scale=1)

    return c.svg(f"{data['name']} — {BANNER_DEK.lower()}")


def _disc_rows(r):
    """Rows of a filled pixel circle: (dy, half_width) with no float artefacts."""
    rows = []
    for dy in range(-r, r + 1):
        half = int((r * r - dy * dy) ** 0.5)
        rows.append((dy, half))
    return rows


def _hill(c, x0, crest, width, color, amp, period, phase, floor):
    """A blocky sine ridge filled down to the floor."""
    import math
    for x in range(x0, x0 + width):
        y = crest + int(round(amp * math.sin((x + phase) * 2 * math.pi / period)))
        c.px(x, y, 1, floor - y, color)


# --- panels -----------------------------------------------------------------

def _panel(c, h, theme):
    c.px(0, 0, W, h, theme["panel"])
    c.rect_outline(0, 0, W, h, theme["panel_edge"], 1)


def draw_stats(data, theme):
    h = 42
    c = Canvas(W, h)
    _panel(c, h, theme)

    # "DAYS IN" rather than followers: a count of days since the account opened
    # moves every single morning, where followers would just print a second 0
    # next to stars. Both are true; only one of them is worth the column.
    cells = [
        ("REPOS", data["repo_count"]),
        ("COMMITS", data["commits"]),
        ("STARS", data["stars"]),
        ("DAYS IN", data["age_days"]),
    ]
    cw = W // len(cells)
    for i, (label, value) in enumerate(cells):
        cx = i * cw + cw // 2
        if i:
            c.px(i * cw, 8, 1, h - 16, theme["bar_off"])
        font.blit_centered(c, str(value), cx, 10, theme["ink"], scale=2)
        font.blit_centered(c, label, cx, 28, theme["muted"], scale=1)
        assert font.width(label, 1) < cw, f"{label!r} overruns its {cw}px column"
    return c.svg("Profile totals: " + ", ".join(f"{v} {k.lower()}" for k, v in cells))


def draw_languages(data, theme):
    langs = data["languages"][:5]
    rows = max(len(langs), 1)
    h = 20 + rows * 13 + 4
    c = Canvas(W, h)
    _panel(c, h, theme)

    font.blit(c, "LANGUAGES", 6, 7, theme["ink"], scale=1)
    font.blit_right(c, "PUBLIC CODE", 214, 7, theme["muted"], scale=1)
    c.px(6, 17, W - 12, 1, theme["bar_off"])

    if not langs:
        font.blit(c, "NO PUBLIC CODE YET", 6, 26, theme["muted"], scale=1)
        return c.svg("Language composition: no public code yet.")

    # Reserve the widest percentage the column can hold, then let the bar have
    # what is left. "100%" is the worst case and it is exactly the one that
    # overlapped when these numbers were guessed by hand.
    pct_col = font.width("100%", 1)
    bar_x0, bar_x1 = 70, 214 - pct_col - 8
    blocks, gap = 20, 1
    bw = (bar_x1 - bar_x0 + gap) // blocks - gap

    for i, (name, pct) in enumerate(langs):
        y = 22 + i * 13
        font.blit(c, font.fit(name, bar_x0 - 12, 1), 6, y, theme["ink"], scale=1)
        filled = max(1, int(round(pct / 100 * blocks)))
        color = art.lang_color(name, theme)
        for b in range(blocks):
            c.px(bar_x0 + b * (bw + gap), y, bw, 7,
                 color if b < filled else theme["bar_off"])
        font.blit_right(c, f"{pct:.0f}%", 214, y, theme["muted"], scale=1)

    summary = ", ".join(f"{n} {p:.0f}%" for n, p in langs)
    return c.svg("Language composition: " + summary)


GARDEN_CELL, GARDEN_PITCH, GARDEN_TOP = 3, 4, 18


def draw_garden(data, theme):
    # Height falls out of the grid instead of being guessed: the legend and the
    # cells collided the first time these were two independent magic numbers.
    grid_h = 7 * GARDEN_PITCH - (GARDEN_PITCH - GARDEN_CELL)
    legend_y = GARDEN_TOP + grid_h + 6
    h = legend_y + 7 + 5
    c = Canvas(W, h)
    _panel(c, h, theme)
    ramp = theme["garden"]

    font.blit(c, "CONTRIBUTION GARDEN", 6, 7, theme["ink"], scale=1)

    weeks = data["calendar"]
    if weeks:
        total = data["total_contributions"]
        font.blit_right(c, f"{total} THIS YEAR", 214, 7, theme["muted"], scale=1)
    else:
        # No token, no calendar. Draw the empty bed and say so rather than
        # printing a zero that reads as "this person did nothing".
        weeks = [[0] * 7 for _ in range(53)]
        font.blit_right(c, "AWAITING SYNC", 214, 7, theme["muted"], scale=1)

    weeks = weeks[-53:]
    peak = max((d for w in weeks for d in w), default=0)
    grid_x = (W - (len(weeks) * GARDEN_PITCH - (GARDEN_PITCH - GARDEN_CELL))) // 2
    for wi, week in enumerate(weeks):
        for di, count in enumerate(week):
            c.px(grid_x + wi * GARDEN_PITCH, GARDEN_TOP + di * GARDEN_PITCH,
                 GARDEN_CELL, GARDEN_CELL, ramp[_level(count, peak)])

    font.blit(c, "LESS", 6, legend_y, theme["muted"], scale=1)
    for i, color in enumerate(ramp):
        c.px(35 + i * 5, legend_y + 1, 4, 4, color)
    font.blit(c, "MORE", 63, legend_y, theme["muted"], scale=1)

    label = (f"Contribution calendar: {data['total_contributions']} in the last year"
             if data["calendar"] else "Contribution calendar: awaiting first sync")
    return c.svg(label)


def _level(count, peak):
    if count <= 0:
        return 0
    if peak <= 0:
        return 1
    for i, cut in enumerate((0.25, 0.5, 0.75)):
        if count <= peak * cut:
            return i + 1
    return 4


def draw_repos(data, theme):
    repos = data["repos"][:4]
    rows = max(len(repos), 1)
    h = 20 + rows * 26 + 2
    c = Canvas(W, h)
    _panel(c, h, theme)

    font.blit(c, "REPOSITORIES", 6, 7, theme["ink"], scale=1)
    font.blit_right(c, f"{data['repo_count']} PUBLIC", 214, 7, theme["muted"], scale=1)
    c.px(6, 17, W - 12, 1, theme["bar_off"])

    if not repos:
        font.blit(c, "NOTHING PUBLIC YET", 6, 26, theme["muted"], scale=1)
        return c.svg("Repositories: none public yet.")

    left, right = 20, 208
    for i, repo in enumerate(repos):
        y = 22 + i * 26
        c.rect_outline(6, y, W - 12, 22, theme["bar_off"], 1)

        lang = repo.get("language")
        if lang:
            c.px(12, y + 5, 4, 4, art.lang_color(lang, theme))

        # Line one: name, with the push time right-aligned. Line two: the
        # description, with the star count right-aligned. Splitting them is what
        # gives the name enough room to survive uncut.
        stamp = ghdata.ago(repo.get("pushed_at"), data["generated"])
        font.blit_right(c, stamp, right, y + 4, theme["muted"], scale=1)
        name_room = right - font.width(stamp, 1) - 8 - left
        font.blit(c, font.fit(repo["name"], name_room, 1), left, y + 4,
                  theme["ink"], scale=1)

        stars = f"* {repo.get('stargazers_count', 0)}"
        font.blit_right(c, stars, right, y + 12, theme["muted"], scale=1)
        desc_room = right - font.width(stars, 1) - 8 - left
        desc = (repo.get("description") or "no description").upper()
        font.blit(c, font.fit(desc, desc_room, 1), left, y + 12,
                  theme["muted"], scale=1)

    names = ", ".join(r["name"] for r in repos)
    return c.svg("Repositories: " + names)


# --- driver -----------------------------------------------------------------

PANELS = {
    "banner": draw_banner,
    "stats": draw_stats,
    "languages": draw_languages,
    "garden": draw_garden,
    "repos": draw_repos,
}


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    print(f"fetching github data for {USER} ...")
    data = ghdata.fetch(USER)
    print(f"  {data['repo_count']} repos, {data['commits']} commits, "
          f"{data['stars']} stars, {len(data['languages'])} languages")
    for note in data["notes"]:
        print(f"  note: {note}")

    written = 0
    for name, fn in PANELS.items():
        for theme in art.THEMES:
            path = ASSETS / f"{name}-{theme['name']}.svg"
            path.write_text(fn(data, theme), encoding="utf-8")
            written += 1
            print(f"  wrote {path.relative_to(ROOT)}")
    print(f"done: {written} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
