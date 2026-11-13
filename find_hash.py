#!/usr/bin/env python3
"""Find which OBB entries contain a texture hash (e.g. the jersey_uh000 texture 0xC82D2341).

  python find_hash.py /sdcard/main.obb
  python find_hash.py /sdcard/main.obb --hash 0xC82D2341 --hash 0xBF7D5FA1 --export /sdcard/found
Reads only; main.obb is never changed.  --export writes each matching IFF to the folder.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from nba2k20 import iff_core as core
from nba2k20.service import Workspace

DEFAULT_HASHES = (0xC82D2341, 0xBF7D5FA1, 0xCDC20195)  # jersey_uh000, shorts_uh003, jersey_uh013


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("obb")
    ap.add_argument("--hash", action="append", help="texture hash, e.g. 0xC82D2341 (repeatable)")
    ap.add_argument("--max-size", type=int, default=4_000_000, help="skip entries bigger than this (bytes)")
    ap.add_argument("--export", help="folder to write the matching IFFs to")
    args = ap.parse_args()
    hashes = [int(h, 16) if h.lower().startswith("0x") else int(h, 16) for h in (args.hash or [])] or list(DEFAULT_HASHES)
    needles = {h: struct.pack("<I", h) for h in hashes}

    ws = Workspace()
    ws.open_obb(args.obb)
    session = ws._need_obb()
    rows = ws.obb_rows("", editable_only=True)
    print(f"scanning {len(rows)} IFF entries for {', '.join(f'0x{h:08X}' for h in hashes)} ...", flush=True)
    found = 0
    for n, row in enumerate(rows, 1):
        if n % 250 == 0:
            print(f"  {n}/{len(rows)} ...", flush=True)
        if row["length"] > args.max_size:
            continue
        try:
            data = core.decompress_wrapper(session.read_entry_raw(row["index"]))[0]
        except Exception:
            continue
        for h, needle in needles.items():
            pos = data.find(needle)
            if pos >= 0:
                found += 1
                print(f"FOUND 0x{h:08X}  entry {row['index']}  {row['label']}  "
                      f"{row['length']:,} B  at decoded 0x{pos:X}", flush=True)
                if args.export:
                    folder = Path(args.export)
                    folder.mkdir(parents=True, exist_ok=True)
                    ws.open_obb_entry(row["index"])
                    print("   wrote", ws.export_obb_iff(folder), flush=True)
    print(f"done, {found} match(es)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
