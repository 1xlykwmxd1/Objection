#!/usr/bin/env python3
"""Find every face texture in the OBB that has a beard, and make contact sheets of them.

  python scan_faces.py /sdcard/main.98.com.t2ksports.nba2k20and.obb
  python scan_faces.py OBB --out /sdcard/NBA2K20Tool/faces --min-beard 0.02 --max-size 3000000

Reads only - the OBB is never changed.  Output folder gets:
  faces.csv           entry index, name, size, texture #, size, beard coverage
  sheet_01.png ...    thumbnails with the ENTRY INDEX written on each (send me these)
Use it to find which entries belong to the Edit Player (create player) heads / beards.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from nba2k20 import iff_core as core
from nba2k20.service import Workspace

THUMB = 128
COLS = 8
ROWS = 6


def beard_cover(img: Image.Image) -> float:
    """Share of the lower-face window that is dark AND low-alpha (how the game marks facial hair)."""
    img = img.convert("RGBA").resize((128, 128))
    w, h = img.size
    box = img.crop((int(0.14 * w), int(0.40 * h), int(0.86 * w), int(0.80 * h)))
    lum = box.convert("L").getdata()
    alp = box.getchannel("A").getdata()
    n = len(lum)
    hit = sum(1 for l, a in zip(lum, alp) if l < 85 and a < 170)
    return hit / n if n else 0.0


def face_of(raw: bytes, name: str):
    """(texture number, WxH, PIL image) of the FACE DIFFUSE texture inside one IFF, else None."""
    opened = core.open_iff_bytes(raw, Path(name))
    for tex in opened.textures:
        if "FACE DIFFUSE" in (tex.label or "").upper() and tex.error is None:
            return tex.number, f"{tex.width}x{tex.height}", core.decode_texture(opened, tex)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("obb")
    ap.add_argument("--out", default="faces_out")
    ap.add_argument("--min-beard", type=float, default=0.02, help="only keep faces with at least this beard share")
    ap.add_argument("--max-size", type=int, default=3_000_000)
    args = ap.parse_args()

    ws = Workspace()
    ws.open_obb(args.obb)
    session = ws._need_obb()
    rows = ws.obb_rows("", editable_only=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"scanning {len(rows)} IFF entries ...", flush=True)

    found = []
    for n, row in enumerate(rows, 1):
        if n % 200 == 0:
            print(f"  {n}/{len(rows)}  faces with beard so far: {len(found)}", flush=True)
        if row["length"] > args.max_size:
            continue
        try:
            raw = session.read_entry_raw(row["index"])
            hit = face_of(raw, f"{row['index']:04d}.iff")
            if hit is None:
                continue
            number, dims, img = hit
            cover = beard_cover(img)
        except Exception:  # noqa: BLE001 - a bad entry must not stop the scan
            continue
        if cover >= args.min_beard:
            found.append({"index": row["index"], "label": row["label"], "size": row["length"],
                          "texture": number, "dims": dims, "beard": round(cover, 3), "img": img})

    found.sort(key=lambda r: r["index"])
    with open(out / "faces.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["index", "label", "size", "texture", "dims", "beard_share"])
        for r in found:
            wr.writerow([r["index"], r["label"], r["size"], r["texture"], r["dims"], r["beard"]])

    per = COLS * ROWS
    for s in range(0, len(found), per):
        sheet = Image.new("RGB", (COLS * THUMB, ROWS * (THUMB + 14)), (20, 22, 30))
        d = ImageDraw.Draw(sheet)
        for k, r in enumerate(found[s:s + per]):
            x, y = (k % COLS) * THUMB, (k // COLS) * (THUMB + 14)
            sheet.paste(r["img"].convert("RGB").resize((THUMB, THUMB)), (x, y + 14))
            d.text((x + 3, y + 1), f"#{r['index']} {r['beard']:.2f}", fill=(255, 255, 255))
        sheet.save(out / f"sheet_{s // per + 1:02d}.png")
    print(f"done: {len(found)} bearded faces -> {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
