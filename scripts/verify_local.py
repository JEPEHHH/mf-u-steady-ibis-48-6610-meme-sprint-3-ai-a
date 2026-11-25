#!/usr/bin/env python3
"""Local verification for the entry, mirroring every written check of the gate.

It runs `main.py` twice, the way the harness does (once per run of the
determinism pair), and holds each output to what the rules say the sealed scorer
checks, plus the two things this competition adds:

  * the file is a whole PNG (signature, chunk framing, every CRC, a complete
    IDAT stream that inflates to exactly the pixels its IHDR declares),
  * it is at most 1 MiB (1,048,576 bytes) and exactly 1024 by 1024 pixels,
  * the run stays well inside the 60 second wall budget, and
  * the two runs are byte for byte identical, because a grade runs the entry
    twice and compares the manifests.

Usage:  python3 scripts/verify_local.py [--keep]

Exit code 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE_BYTES = 1024 * 1024
GATE_SIZE = 1024
WALL_BUDGET_SEC = 60


class CheckFailed(Exception):
    """A check that did not pass."""


def run_entry(workdir: str) -> tuple[bytes, float]:
    """Run main.py with MAKEFUN_OUTPUT_DIR set to `workdir`; return the file's bytes and wall time."""
    env = dict(os.environ, MAKEFUN_OUTPUT_DIR=workdir)
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO, "main.py")],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=WALL_BUDGET_SEC * 2,
    )
    wall = time.monotonic() - started
    if proc.returncode != 0:
        raise CheckFailed(f"main.py exited {proc.returncode}: {(proc.stderr or '').strip()[-400:]}")
    path = os.path.join(workdir, "entry.png")
    if not os.path.isfile(path):
        raise CheckFailed("main.py wrote no entry.png")
    if proc.stdout.strip():
        print(f"        entry reported {proc.stdout.strip()}")
    with open(path, "rb") as fh:
        return fh.read(), wall


def read_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    """Every chunk of a PNG, as (kind, payload)."""
    out: list[tuple[bytes, bytes]] = []
    i = 8
    while i < len(data):
        (length,) = struct.unpack(">I", data[i : i + 4])
        kind = data[i + 4 : i + 8]
        payload = data[i + 8 : i + 8 + length]
        (crc,) = struct.unpack(">I", data[i + 8 + length : i + 12 + length])
        if len(payload) != length or len(data) < i + 12 + length:
            raise CheckFailed(f"chunk {kind!r} is truncated")
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise CheckFailed(f"chunk {kind!r} has a bad CRC")
        out.append((kind, payload))
        i += 12 + length
    return out


def check_png(data: bytes) -> tuple[int, int]:
    """Hold `data` to the gate's image rules; return its (width, height)."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise CheckFailed("the file is not a PNG (bad signature)")
    chunks = read_chunks(data)
    kinds = [k for k, _ in chunks]
    if kinds[0] != b"IHDR":
        raise CheckFailed("the first chunk is not IHDR")
    if kinds[-1] != b"IEND":
        raise CheckFailed("the last chunk is not IEND")
    if kinds.count(b"IHDR") != 1 or kinds.count(b"IEND") != 1:
        raise CheckFailed("the file carries more than one IHDR or IEND")
    if b"IDAT" not in kinds:
        raise CheckFailed("the file carries no IDAT")
    width, height, depth, color_type, compression, filt, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
    if (depth, color_type, compression, filt, interlace) != (8, 2, 0, 0, 0):
        raise CheckFailed(f"unexpected PNG format: depth {depth}, colour type {color_type}, interlace {interlace}")
    if (width, height) != (GATE_SIZE, GATE_SIZE):
        raise CheckFailed(f"the image is {width}x{height}, the gate wants at most {GATE_SIZE}x{GATE_SIZE}")
    raw = zlib.decompress(b"".join(p for k, p in chunks if k == b"IDAT"))
    expected = height * (1 + width * 3)
    if len(raw) != expected:
        raise CheckFailed(f"the pixels inflate to {len(raw)} bytes, expected {expected}")
    if len(data) > GATE_BYTES:
        raise CheckFailed(f"the file is {len(data)} bytes, over the {GATE_BYTES} the gate allows")
    return width, height


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true", help="keep the rendered runs for inspection")
    args = parser.parse_args()

    root = tempfile.mkdtemp(prefix="verify-entry-", dir=os.environ.get("TMPDIR") or None)
    passed = 0
    try:
        runs: list[tuple[bytes, float]] = []
        for i in (1, 2):
            work = os.path.join(root, f"run{i}")
            os.makedirs(work, exist_ok=True)
            print(f"[{i}/2] rendering (MAKEFUN_OUTPUT_DIR={work})")
            runs.append(run_entry(work))

        print("[..] checking the PNG is whole, 1024x1024 and under 1 MiB")
        for n, (data, _) in enumerate(runs, start=1):
            width, height = check_png(data)
            print(f"        run {n}: {width}x{height}, {len(data)} bytes ({len(data) / 1024:.1f} KiB)")
            passed += 1

        slowest = max(wall for _, wall in runs)
        print(f"[..] checking the wall time against the {WALL_BUDGET_SEC} s budget")
        if slowest >= WALL_BUDGET_SEC:
            raise CheckFailed(f"the slowest run took {slowest:.2f} s, the budget is {WALL_BUDGET_SEC} s")
        print(f"        slowest run {slowest:.2f} s")
        passed += 1

        print("[..] checking the two runs are byte for byte identical")
        if runs[0][0] != runs[1][0]:
            raise CheckFailed("the two runs differ, so the entry is not deterministic")
        print("        identical")
        passed += 1

        print(f"\nall {passed} checks passed")
        print(f"entry: {len(runs[0][0])} bytes, byte for byte stable")
        return 0
    except CheckFailed as err:
        print(f"\nFAILED: {err}", file=sys.stderr)
        return 1
    finally:
        if args.keep:
            print(f"kept the runs under {root}")
        else:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
