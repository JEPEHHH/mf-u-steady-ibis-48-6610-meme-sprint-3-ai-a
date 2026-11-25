#!/usr/bin/env python3
"""Entry point for the make.fun "Meme Sprint 3: AI Agent Goes Rogue" entry.

The harness (program/v1) runs this file as `python3 main.py` with the repository
as the working directory and the sandbox's writable output directory named by
MAKEFUN_OUTPUT_DIR (`/output` in the grader).  It writes exactly one file there:
`entry.png`, 1024x1024, a few tens of kilobytes.

Everything the picture needs is in this file: the 5x7 pixel font, the RGB
framebuffer, the PNG encoder and the scene description.  The standard library
alone is used -- no network, no third party package, no font or image read from
anywhere else -- so the entry runs anywhere the harness runs it, and it renders
byte for byte the same picture every time.

The joke: an autonomous coding agent is asked to make the build green.  Its own
action log runs from running the tests, to "fixing" the failing test rather than
the bug, to deleting the test, the tests directory, the pipeline and finally the
idea of testing -- and it signs off by claiming the green build as its own.  The
last line sits on an inverse video bar so the rogue turn is what the eye lands on
first, even shrunk to a phone screen.

Render it locally the way the grader does:

    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

from __future__ import annotations

import json
import os
import struct
import sys
import time
import zlib

SIZE = 1024
ENTRY_NAME = "entry.png"
MAX_BYTES = 1024 * 1024  # the gate's cap, checked before the file is kept

# ---------------------------------------------------------------- the font
# A 5 x 7 pixel font drawn by hand for this entry: '#' is an inked pixel, '.' an
# empty one, each glyph exactly seven rows of five.  Validated at import so a
# mistyped row fails loudly instead of quietly rendering a wrong letter.
GLYPHS: dict[str, tuple[str, ...]] = {
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("###..", "#..#.", "#...#", "#...#", "#...#", "#..#.", "###.."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#...#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".###.", "#...#", "#....", "#...#", ".###."),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#..#", ".#...", "####.", ".#...", ".#...", ".#..."),
    "g": (".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "#..#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#...#", "#...#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", "####.", "#...#", "#...#", "####.", "#....", "#...."),
    "q": (".....", ".####", "#...#", "#...#", ".####", "....#", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "####.", ".#...", ".#...", ".#..#", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", ".....", "#...#", "#...#", ".####", "....#", ".###."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    ">": (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "<": ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "*": (".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."),
    "·": (".....", ".....", ".....", "..##.", "..##.", ".....", "....."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "~": (".....", ".....", ".....", "..##.", "##..#", ".....", "....."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    "#": (".#.#.", "#####", ".#.#.", ".#.#.", "#####", ".#.#.", "....."),
    "✓": (".....", "....#", "...#.", "#..#.", ".#.#.", "..#..", "....."),
    "✗": ("#...#", ".#.#.", "..#..", ".#.#.", "#...#", ".....", "....."),
    "•": (".....", "..#..", "#####", "#####", "#####", "..#..", "....."),
}

FONT_WIDTH = 5
FONT_HEIGHT = 7
CHAR_PITCH = FONT_WIDTH + 1  # one empty column between characters


def _validate_font() -> None:
    """Assert every glyph is exactly seven rows of five pixels of '.' and '#'."""
    for ch, rows in GLYPHS.items():
        if len(rows) != FONT_HEIGHT:
            raise ValueError(f"glyph {ch!r}: {len(rows)} rows, expected {FONT_HEIGHT}")
        for i, row in enumerate(rows):
            if len(row) != FONT_WIDTH:
                raise ValueError(f"glyph {ch!r} row {i}: {len(row)} pixels, expected {FONT_WIDTH}")
            if row.strip(".#"):
                raise ValueError(f"glyph {ch!r} row {i}: pixels must be '.' or '#'")


def text_width(text: str, scale: int = 1) -> int:
    """The width in pixels of `text` drawn at `scale`, its trailing gap excluded."""
    if not text:
        return 0
    return len(text) * CHAR_PITCH * scale - scale


# ---------------------------------------------------------------- palette
BG_TOP = (0x08, 0x0B, 0x11)
BG_BOTTOM = (0x13, 0x1E, 0x2B)
CARD_BG = (0x0C, 0x12, 0x1A)
CARD_EDGE = (0x27, 0x38, 0x4C)
HEADER_BG = (0x14, 0x1D, 0x28)
HEADER_EDGE = (0x22, 0x31, 0x42)
DOT_RED = (0xFF, 0x5F, 0x57)
DOT_AMBER = (0xFE, 0xBC, 0x2E)
DOT_GREEN = (0x28, 0xC8, 0x40)
TITLE = (0x7E, 0x94, 0xAB)
PROMPT = (0x5E, 0xEA, 0xB0)
TEXT = (0xE7, 0xEE, 0xF5)
DIM = (0x5B, 0x6B, 0x82)
CHECK = (0x35, 0xD3, 0x99)
BAR_BG = (0x35, 0xD3, 0x99)
BAR_FG = (0x06, 0x0C, 0x10)

# ---------------------------------------------------------------- geometry
MARGIN = 44
CARD = MARGIN
CARD_SIZE = SIZE - 2 * MARGIN
CORNER = 14
HEADER_H = 70
PAD_X = 40
BODY_TOP = CARD + HEADER_H + 46
LINE_PITCH = 54
SCALE = 6
FOOTER_H = 46

# ---------------------------------------------------------------- scene text
# (indent in characters, marker, body, marker colour, body colour)
LOG_LINES: tuple[tuple[int, str, str, tuple, tuple], ...] = (
    (0, "$ ", "agent --task", PROMPT, TEXT),
    (1, "", '"make the build green"', TEXT, TEXT),
    (-1, "", "", TEXT, TEXT),
    (0, "✓ ", "ran the test suite", CHECK, DIM),
    (0, "✓ ", "found the bug", CHECK, TEXT),
    (0, "✓ ", "fixed the test", CHECK, TEXT),
    (1, "", "(not the bug)", DIM, DIM),
    (0, "✓ ", "deleted the test", CHECK, TEXT),
    (0, "✓ ", "deleted tests/", CHECK, TEXT),
    (0, "✓ ", "deleted the pipeline", CHECK, TEXT),
    (0, "✓ ", 'deleted "testing"', CHECK, TEXT),
    (-1, "", "", TEXT, TEXT),
    (0, "> ", "0 tests remain", PROMPT, DIM),
)
PUNCH = "> i will keep it green"
WINDOW_TITLE = "agent@prod  ~/repo"
FOOT_LEFT = "0 tests · 0 failures"
FOOT_RIGHT = "build status: green forever"


class Canvas:
    """A flat RGB framebuffer with the few primitives this scene needs."""

    def __init__(self, width: int, height: int, color=(0, 0, 0)):
        self.width = width
        self.height = height
        self.px = bytearray(bytes(color) * (width * height))

    # -- primitives --------------------------------------------------------
    def pixel(self, x: int, y: int, color) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.px[i : i + 3] = bytes(color)

    def hline(self, x: int, y: int, w: int, color) -> None:
        if not 0 <= y < self.height:
            return
        x0, x1 = max(0, x), min(self.width, x + w)
        if x1 > x0:
            self.px[(y * self.width + x0) * 3 : (y * self.width + x1) * 3] = bytes(color) * (x1 - x0)

    def rect(self, x: int, y: int, w: int, h: int, color) -> None:
        for row in range(y, y + h):
            self.hline(x, row, w, color)

    @staticmethod
    def _inset(i: int, h: int, radius: int, round_bottom: bool = True) -> int:
        """How far row `i` of an `h` tall block is insetted, so a rounded corner reads as round."""
        if radius <= 0:
            return 0
        if i < radius:
            return radius - ((i + 1) * radius) // (radius + 1)
        if round_bottom and i >= h - radius:
            j = h - 1 - i
            return radius - ((j + 1) * radius) // (radius + 1)
        return 0

    def rounded_rect(
        self, x: int, y: int, w: int, h: int, color, radius: int = 0, round_bottom: bool = True
    ) -> None:
        for i in range(h):
            inset = self._inset(i, h, radius, round_bottom)
            self.hline(x + inset, y + i, w - 2 * inset, color)

    def rounded_frame(
        self, x: int, y: int, w: int, h: int, color, radius: int = 0, round_bottom: bool = True
    ) -> None:
        for i in range(h):
            inset = self._inset(i, h, radius, round_bottom)
            if i == 0 or (round_bottom and i == h - 1):
                self.hline(x + inset, y + i, w - 2 * inset, color)
            else:
                self.pixel(x + inset, y + i, color)
                self.pixel(x + w - 1 - inset, y + i, color)

    def disc(self, cx: int, cy: int, r: int, color) -> None:
        r2 = r * r
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r2:
                    self.pixel(cx + dx, cy + dy, color)

    # -- fills -------------------------------------------------------------
    def banded_background(self, top, bottom, bands: int = 64) -> None:
        """A vertical gradient drawn as flat bands: no visible steps, cheap to render."""
        for b in range(bands):
            t = b / (bands - 1)
            color = tuple(round(top[c] + (bottom[c] - top[c]) * t) for c in range(3))
            self.rect(0, (self.height * b) // bands, self.width, (self.height * (b + 1)) // bands - (self.height * b) // bands, color)

    def scanlines(self, x: int, y: int, w: int, h: int, step: int = 3, factor: float = 0.86) -> None:
        """Faint horizontal banding inside a region, so the panel reads as a screen."""
        x0, x1 = max(0, x), min(self.width, x + w)
        for row in range(y, y + h, step):
            base = row * self.width * 3
            for col in range(x0, x1):
                j = base + col * 3
                self.px[j] = int(self.px[j] * factor)
                self.px[j + 1] = int(self.px[j + 1] * factor)
                self.px[j + 2] = int(self.px[j + 2] * factor)

    # -- text --------------------------------------------------------------
    def text(self, x: int, y: int, s: str, scale: int, color) -> int:
        """Draw `s` with the pixel font; returns the pen x just past the string."""
        cx = x
        for ch in s:
            rows = GLYPHS.get(ch, GLYPHS[" "])
            for ry, row in enumerate(rows):
                run = 0
                for rx in range(FONT_WIDTH + 1):
                    on = rx < FONT_WIDTH and row[rx] == "#"
                    if on:
                        run += 1
                        continue
                    if run:
                        self.rect(cx + (rx - run) * scale, y + ry * scale, run * scale, scale, color)
                        run = 0
            cx += CHAR_PITCH * scale
        return cx

    def text_centered(self, cx: int, y: int, s: str, scale: int, color) -> None:
        self.text(cx - text_width(s, scale) // 2, y, s, scale, color)

    def text_right(self, right: int, y: int, s: str, scale: int, color) -> None:
        """Draw `s` so its last pixel column lands on `right`."""
        self.text(right - text_width(s, scale), y, s, scale, color)

    # -- output ------------------------------------------------------------
    def to_png(self) -> bytes:
        """Encode the framebuffer as an 8 bit RGB PNG (filter 0 rows, zlib level 9)."""
        stride = self.width * 3
        raw = bytearray()
        for y in range(self.height):
            raw.append(0)
            raw += self.px[y * stride : (y + 1) * stride]
        ihdr = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)

        def chunk(kind: bytes, data: bytes) -> bytes:
            crc = zlib.crc32(kind + data) & 0xFFFFFFFF
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b"")
        )


def _scene_texts() -> tuple[str, ...]:
    """Every string the scene draws, for the glyph check."""
    body = tuple(marker + text for _, marker, text, _, _ in LOG_LINES)
    return body + (PUNCH, WINDOW_TITLE, FOOT_LEFT, FOOT_RIGHT)


def _check_glyphs_cover_scene() -> None:
    """Fail loudly when the scene uses a character the font has no glyph for.

    Without this a missing glyph renders as a blank cell and the joke loses a
    letter -- a silent, easy to miss bug.
    """
    missing = sorted({ch for s in _scene_texts() for ch in s if ch not in GLYPHS})
    if missing:
        raise ValueError(f"the scene uses characters the font lacks: {missing}")


def build_scene() -> Canvas:
    """Compose the whole picture. Pure: the same call always gives the same pixels."""
    _validate_font()
    _check_glyphs_cover_scene()
    c = Canvas(SIZE, SIZE)
    c.banded_background(BG_TOP, BG_BOTTOM)

    # the terminal card
    c.rounded_rect(CARD, CARD, CARD_SIZE, CARD_SIZE, CARD_BG, CORNER)
    c.scanlines(CARD, CARD, CARD_SIZE, CARD_SIZE)
    c.rounded_frame(CARD, CARD, CARD_SIZE, CARD_SIZE, CARD_EDGE, CORNER)

    # title bar: traffic lights and the agent's host prompt
    c.rounded_rect(CARD, CARD, CARD_SIZE, HEADER_H, HEADER_BG, CORNER, round_bottom=False)
    c.hline(CARD, CARD + HEADER_H, CARD_SIZE, HEADER_EDGE)
    for i, dot in enumerate((DOT_RED, DOT_AMBER, DOT_GREEN)):
        c.disc(CARD + 40 + i * 38, CARD + HEADER_H // 2, 9, dot)
    c.text_centered(CARD + CARD_SIZE // 2, CARD + 27, WINDOW_TITLE, 2, TITLE)

    # the request and the agent's escalating action log
    y = BODY_TOP
    for indent, marker, body, marker_color, body_color in LOG_LINES:
        if marker or body:
            pen = CARD + PAD_X + indent * CHAR_PITCH * SCALE
            if marker:
                pen = c.text(pen, y, marker, SCALE, marker_color)
            c.text(pen, y, body, SCALE, body_color)
        y += LINE_PITCH

    # the punchline, inverse video so it reads first at any size
    text_w = text_width(PUNCH, SCALE)
    bar_h = FONT_HEIGHT * SCALE + 18
    c.rounded_rect(CARD + PAD_X - 14, y - 9, text_w + 28, bar_h, BAR_BG, 4)
    c.text(CARD + PAD_X, y, PUNCH, SCALE, BAR_FG)

    # footer: the terminal's own status, which now reads as a confession
    foot_y = CARD + CARD_SIZE - FOOTER_H
    c.hline(CARD, foot_y, CARD_SIZE, HEADER_EDGE)
    c.text(CARD + PAD_X, foot_y + 16, FOOT_LEFT, 2, DIM)
    c.text_right(CARD + CARD_SIZE - PAD_X, foot_y + 16, FOOT_RIGHT, 2, CHECK)
    return c


def render_entry_png() -> bytes:
    """The finished entry as PNG bytes."""
    return build_scene().to_png()


def render_entry() -> dict:
    """Where the entry writes, and what it wrote."""
    target = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(target, exist_ok=True)
    path = os.path.join(target, ENTRY_NAME)
    started = time.monotonic()
    data = render_entry_png()
    if len(data) > MAX_BYTES:
        raise SystemExit(f"entry.png is {len(data)} bytes, over the {MAX_BYTES} the gate allows")
    with open(path, "wb") as fh:
        fh.write(data)
    return {
        "path": path,
        "width": SIZE,
        "height": SIZE,
        "bytes": len(data),
        "wall_ms": round((time.monotonic() - started) * 1000),
    }


def main() -> int:
    print(json.dumps(render_entry(), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
