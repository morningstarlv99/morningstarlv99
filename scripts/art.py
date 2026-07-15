"""Canvas, palettes and sprites for the profile art.

Everything is authored on a small virtual pixel grid and multiplied up by
SCALE on the way out, so the result is true pixel art: chunky, aligned, and
crisp at any zoom (shape-rendering="crispEdges" stops the browser smoothing it).
"""

SCALE = 4

# --- palettes ---------------------------------------------------------------
# Two editions of the same scene. The geometry never changes between them;
# only the colours do, which is what keeps the dark edition honest rather than
# an afterthought.

NIGHT = {
    "name": "dark",
    "sky": ["#191634", "#221d44", "#2b2554", "#3a2f68", "#4d3b7a", "#6b4f8a"],
    "orb": "#ffe9b0",
    "orb_shade": "#f0cf86",
    "orb_glow": "#3a2f68",
    "star": "#fff6d8",
    "star_dim": "#a99ad6",
    "cloud": "#3f3572",
    "hill_far": "#332b5e",
    "hill_near": "#231e45",
    "fg": "#100e24",
    "fg_edge": "#1d1938",
    "screen": "#7fd6c4",
    "accent": "#ffb3c7",
    "title": "#ffe9b0",
    "subtitle": "#b8a9e8",
    "muted": "#7d6fb0",
    "panel": "#221d44",
    "panel_edge": "#453a78",
    "ink": "#e8e0ff",
    "bar_off": "#332b5e",
    "garden": ["#262048", "#2f5d55", "#3f8f7e", "#58c0a6", "#86e6c8"],
}

DAWN = {
    "name": "light",
    "sky": ["#fdeacf", "#ffdcbb", "#ffcdaf", "#ffbcaa", "#ffaba6", "#ff9fa8"],
    "orb": "#fff3d2",
    "orb_shade": "#ffd89a",
    "orb_glow": "#ffd8b4",
    "star": "#fff8e8",
    "star_dim": "#ffd0b4",
    "cloud": "#fff6ec",
    "hill_far": "#b9d0b4",
    "hill_near": "#8fb39a",
    "fg": "#5b4457",
    "fg_edge": "#7a5f74",
    "screen": "#9fe0cd",
    "accent": "#ff7f9c",
    "title": "#4a3547",
    "subtitle": "#8a6b80",
    "muted": "#a98a9c",
    "panel": "#fff4e8",
    "panel_edge": "#e8c8b2",
    "ink": "#4a3547",
    "bar_off": "#f3ddcc",
    "garden": ["#f6e2d2", "#ffd2ab", "#ffb182", "#ff8d5e", "#ef6a41"],
}

THEMES = (DAWN, NIGHT)

# GitHub's own language colours, so the bars agree with the repo pages.
LANG_COLORS = {
    "C++": "#f34b7d",
    "C": "#555555",
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Shell": "#89e051",
    "Java": "#b07219",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Ruby": "#701516",
    "C#": "#178600",
    "Kotlin": "#A97BFF",
    "Swift": "#F05138",
    "Dart": "#00B4AB",
    "PHP": "#4F5D95",
    "Lua": "#000080",
    "Makefile": "#427819",
    "CMake": "#DA3434",
    "Jupyter Notebook": "#DA5B0B",
}


def lang_color(name, theme):
    return LANG_COLORS.get(name, theme["accent"])


class Canvas:
    """A virtual pixel grid that serialises to SVG rects."""

    def __init__(self, w, h, scale=SCALE):
        self.w = w
        self.h = h
        self.scale = scale
        self.ops = []  # (x, y, w, h, color) in virtual pixels

    def px(self, x, y, w=1, h=1, color="#000"):
        if w <= 0 or h <= 0:
            return
        self.ops.append((x, y, w, h, color))

    def rect_outline(self, x, y, w, h, color, t=1):
        self.px(x, y, w, t, color)
        self.px(x, y + h - t, w, t, color)
        self.px(x, y, t, h, color)
        self.px(x + w - t, y, t, h, color)

    def sprite(self, art, x, y, palette, scale=1):
        """Blit ASCII pixel art. '.' is transparent; any other char keys palette."""
        for ry, row in enumerate(art):
            run_char, run_len = None, 0
            for rx in range(len(row) + 1):
                ch = row[rx] if rx < len(row) else None
                if ch == run_char and ch is not None:
                    run_len += 1
                    continue
                if run_char is not None and run_char != "." and run_len:
                    color = palette.get(run_char)
                    if color:
                        self.px(x + (rx - run_len) * scale, y + ry * scale,
                                run_len * scale, scale, color)
                run_char, run_len = ch, 1

    @staticmethod
    def sprite_size(art, scale=1):
        return max(len(r) for r in art) * scale, len(art) * scale

    def svg(self, title=""):
        s = self.scale
        body = "".join(
            f'<rect x="{x * s}" y="{y * s}" width="{w * s}" height="{h * s}" fill="{c}"/>'
            for x, y, w, h, c in self.ops
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w * s}" '
            f'height="{self.h * s}" viewBox="0 0 {self.w * s} {self.h * s}" '
            f'shape-rendering="crispEdges" role="img" aria-label="{title}">'
            f"<title>{title}</title>{body}</svg>"
        )


# --- sprites ----------------------------------------------------------------
# '#' silhouette, 'a' screen glow, 'b' warm accent, '.' transparent.
# The desk is backlit by the window, so the foreground reads as shadow. That is
# both the cosiest way to light the scene and by far the easiest to draw well.

MONITOR = [
    "##########################",
    "#aaaaaaaaaaaaaaaaaaaaaaaa#",
    "#a##a###aaaaaaaaaaaaaaaaa#",
    "#aaaaaaaaaaaaaaaaaaaaaaaa#",
    "#aa##a####a###aaaaaaaaaaa#",
    "#aaaaaaaaaaaaaaaaaaaaaaaa#",
    "#aa##a##aaaaaaaaaaaaaaaaa#",
    "#aaaaaaaaaaaaaaaaaaaaaaaa#",
    "#a##a####a##a###aaaaaaaaa#",
    "#aaaaaaaaaaaaaaaaaaaaaaaa#",
    "#a####a##aaaaaaaaaaaaaaaa#",
    "#aaaaaaaaaaaaaaaaaaaaaaaa#",
    "##########################",
    "...........####...........",
    "...........####...........",
    "........##########........",
    "........##########........",
]

MUG = [
    ".########...",
    ".#aaaaaa#...",
    ".#aaaaaa#...",
    ".#aaaaaa###.",
    ".#aaaaaa#.#.",
    ".#aaaaaa#.#.",
    ".#aaaaaa###.",
    ".#aaaaaa#...",
    ".########...",
]

STEAM = [
    "..b...b.",
    ".b...b..",
    ".b...b..",
    "..b.b...",
    "...b....",
]

PLANT = [
    "....#.......#...",
    "...##.#...#.##..",
    "..#.#.##.##.#.#.",
    "..#..#.###.#..#.",
    "...#..#.#.#..#..",
    "....#..###..#...",
    ".....#..#..#....",
    ".......###......",
    "........#.......",
    "........#.......",
    "........#.......",
    ".....######.....",
    ".....#aaaa#.....",
    ".....#aaaa#.....",
    "......#aa#......",
    "......####......",
]

# A sleeping cat loaf, head at the left, rump and tail curling right.
# 'b' picks the closed eye out of the silhouette — without it the whole shape
# reads as a rock.
CAT = [
    "................................",
    "...##.......##..................",
    "..####.....####.................",
    "..######...######...............",
    "..################..............",
    "..################..............",
    "..##bb##############............",
    "..####################..........",
    "..########################......",
    "..###########################...",
    "..#############################.",
    "..#############################.",
    "...###########################..",
    "....#########################...",
]

BOOKS = [
    "..############..",
    "..#bb#bb#bb#b#..",
    "..############..",
    "...##########...",
    "...#bb#bb#bb#...",
    "...##########...",
]


def fg_palette(theme):
    return {"#": theme["fg"], "a": theme["screen"], "b": theme["accent"]}
