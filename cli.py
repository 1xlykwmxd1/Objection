#!/usr/bin/env python3
"""NBA 2K20 OBB / IFF tool - command line (Termux, Linux, Windows).

Examples
--------
  python cli.py obb list main.obb --search UA0
  python cli.py obb export-png main.obb 12 out_png
  python cli.py obb patch main.obb main_patched.obb --png 12:out_png
  python cli.py port14 png1013.iff --out ported        (2K14 -> 2K20 on the built-in base; --base MY.iff for your own)
  python cli.py iff list UA000.IFF
  python cli.py iff replace-folder UA000.IFF edited_png --output UA000_EDITED.IFF
  python cli.py scene export-obj scoreboard.iff --output scoreboard.obj   (then scene import-obj)
  python cli.py scene objects arena.iff --grep score   /   scene move arena.iff NAME --dy 2.5 --output out.iff
  python cli.py scoreboard list newscorebug.iff   /   scoreboard move newscorebug.iff 3 --x -120 --y -170 --output out.iff
"""

from __future__ import annotations

import argparse
import json
import sys
import zlib
from pathlib import Path

try:
    from nba2k20 import iff_core as core
    from nba2k20.service import Workspace, WorkspaceError
except ModuleNotFoundError as _missing:
    if _missing.name == "PIL":
        print(
            "\n[-] Kulang ang Pillow (PIL) - kailangan ito para magbasa/magsulat ng texture PNG.\n\n"
            "    I-install muna:\n"
            "        pip install pillow\n\n"
            "    Kung mag-error yan sa pag-build sa Termux, i-try muna:\n"
            "        pkg update\n"
            "        pkg install python libjpeg-turbo libpng zlib freetype -y\n"
            "        pip install pillow\n\n"
            "    Pagkatapos, i-verify:\n"
            "        python -c \"import PIL; print(PIL.__version__)\"\n\n"
            "    Tapos ulitin mo yung command mo.\n",
            file=sys.stderr,
        )
    else:
        print(
            f"\n[-] Kulang ang Python package na '{_missing.name}'.\n\n"
            f"    I-install: pip install {_missing.name}\n",
            file=sys.stderr,
        )
    sys.exit(1)


def _dump(value) -> None:
    print(json.dumps(value, indent=2, default=str))


def _split_pair(text: str, what: str) -> tuple[int, Path]:
    index_text, separator, path_text = text.partition(":")
    if not separator or not index_text.isdigit() or not path_text:
        raise ValueError(f"{what} must look like INDEX:PATH, got {text!r}")
    return int(index_text), Path(path_text)


# ---------------------------------------------------------------- iff group
def cmd_iff_list(args, ws: Workspace) -> int:
    ws.open_iff(args.file)
    _dump(ws.opened.summary() if args.full else ws.opened_summary())
    if not args.full:
        for row in ws.texture_rows():
            note = "" if row["decodable"] else f"  [{row['error']}]"
            print(
                f"  #{row['number']:<3} {row['width']}x{row['height']:<5} "
                f"{row['format']:<11} {row['label']}{note}"
            )
    return 0


def cmd_iff_export_png(args, ws: Workspace) -> int:
    ws.open_iff(args.file)
    count, errors = ws.export_all_textures(args.folder)
    print(f"exported {count} texture(s) to {args.folder}")
    for error in errors:
        print(f"warning: {error}", file=sys.stderr)
    return 0


def cmd_iff_export_resources(args, ws: Workspace) -> int:
    ws.open_iff(args.file)
    count, covered = ws.export_all_resources(args.folder)
    print(
        f"exported {count} resource file(s) covering "
        f"{covered}/{len(ws.opened.data)} decompressed bytes to {args.folder}"
    )
    return 0


def _iff_apply_and_save(args, ws: Workspace) -> int:
    ws.open_iff(args.file)
    changes = []
    for number_text, png in getattr(args, "texture", None) or []:
        changes.append(ws.import_texture(int(number_text), Path(png)))
    batch = None
    if getattr(args, "folder", None):
        batch = ws.import_texture_folder(args.folder)
    save = ws.save_iff(args.output, allow_overwrite=args.force)
    _dump({"changes": changes, "batch": batch, "save": save})
    return 0


def cmd_iff_scan(args, ws: Workspace) -> int:
    folder = args.folder.resolve()
    errors: list[str] = []
    files = core.find_iff_files(folder, errors=errors)
    _dump(
        {
            "folder": str(folder),
            "count": len(files),
            "files": [str(path.relative_to(folder)) for path in files],
            "errors": errors,
            "incomplete": bool(errors),
        }
    )
    return 0


def cmd_iff_catalog(args, ws: Workspace) -> int:
    def report(index, total, path, outcome, error_text) -> None:
        if outcome == "error" or index == total or index % 100 == 0:
            suffix = f": {error_text}" if error_text else ""
            print(f"[{index}/{total}] {path.name} {outcome}{suffix}", flush=True)

    _dump(core.build_folder_catalog(args.folder, progress=report))
    return 0


# ---------------------------------------------------------------- obb group
def cmd_obb_list(args, ws: Workspace) -> int:
    info = ws.open_obb(args.obb)
    print(
        f"{info['path']}  {info['size']:,} bytes  "
        f"{info['entries']} entries, {info['editable_iff_entries']} editable IFF"
    )
    for row in ws.obb_rows(args.search or "", editable_only=not args.all):
        flag = "*" if row["staged"] else " "
        print(
            f"{flag}{row['index']:>5}  {row['label']:<18} {row['type']:<10} "
            f"{row['length']:>11,} B  hash {row['hash']}"
        )
    return 0


def cmd_obb_unknown(args, ws: Workspace) -> int:
    """Report entries whose file name is unknown, with their block layout (to find court/logo signatures)."""
    ws.open_obb(args.obb)
    session = ws._need_obb()
    lines = ["index,hash,type,length,blocks"]
    for row in ws.obb_rows("", editable_only=True):
        if row["category"] in ("Custom",) or row["label"] == row["hash"]:
            sizes = session.block_sizes(row["index"])
            lines.append(f"{row['index']},{row['hash']},{row['type']},{row['length']},{'|'.join(map(str, sizes))}")
    text = "\n".join(lines)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"{len(lines) - 1} unknown entries -> {args.output}")
    else:
        print(text)
    return 0


def cmd_obb_textures(args, ws: Workspace) -> int:
    ws.open_obb(args.obb)
    ws.open_obb_entry(args.index)
    _dump(ws.opened_summary())
    for row in ws.texture_rows():
        note = "" if row["decodable"] else f"  [{row['error']}]"
        print(
            f"  #{row['number']:<3} {row['width']}x{row['height']:<5} "
            f"{row['format']:<11} {row['label']}{note}"
        )
    return 0


def cmd_obb_export_png(args, ws: Workspace) -> int:
    ws.open_obb(args.obb)
    ws.open_obb_entry(args.index)
    count, errors = ws.export_all_textures(args.folder)
    print(f"exported {count} texture(s) to {args.folder}")
    for error in errors:
        print(f"warning: {error}", file=sys.stderr)
    return 0


def cmd_obb_export_iff(args, ws: Workspace) -> int:
    ws.open_obb(args.obb)
    ws.open_obb_entry(args.index)
    print(f"wrote {ws.export_obb_iff(args.destination)}")
    return 0


def cmd_obb_import_iff(args, ws: Workspace) -> int:
    """Import IFF: replace one entry with a complete IFF (any file name) and write a new OBB."""
    ws.open_obb(args.obb)
    ws.open_obb_entry(args.index)
    result = ws.replace_obb_iff(args.file, check_name=False)
    print(f"entry {args.index}: staged replacement ({result['mode']})")
    _dump(ws.save_obb(args.output, allow_overwrite=args.force,
                      progress=lambda message: print(message, flush=True)))
    return 0


def cmd_obb_patch(args, ws: Workspace) -> int:
    """Apply PNG folders / replacement IFFs to several entries and rebuild the OBB."""
    if not args.png and not args.iff:
        raise ValueError("give at least one --png INDEX:FOLDER or --iff INDEX:FILE")
    ws.open_obb(args.obb)
    for text in args.png or []:
        index, folder = _split_pair(text, "--png")
        ws.open_obb_entry(index)
        report = ws.import_texture_folder(folder)
        print(f"entry {index}: imported {len(report['changes'])} PNG(s)")
        ws.stage_current()
    for text in args.iff or []:
        index, source = _split_pair(text, "--iff")
        ws.open_obb_entry(index)
        result = ws.replace_obb_iff(source, check_name=False)  # the entry index is explicit
        print(f"entry {index}: staged replacement ({result['mode']})")
    report = ws.save_obb(
        args.output,
        allow_overwrite=args.force,
        progress=lambda message: print(message, flush=True),
    )
    _dump(report)
    return 0


def cmd_uv(args, ws):
    """UV grid maker: grid over an image -> flattened PNG, overlay PNG, OBJ and JSON."""
    from PIL import Image
    from nba2k20 import uvgrid

    image = Image.open(args.image).convert("RGBA")
    if args.load:
        grid = uvgrid.UVGrid.from_json(Path(args.load).read_text(encoding="utf-8"))
    else:
        grid = uvgrid.UVGrid.regular(*uvgrid.parse_grid_size(args.grid))
    for text in args.move or []:
        try:
            col, row, x, y = text.split(",")
            grid.move(grid.index(int(col), int(row)), float(x), float(y))
        except (ValueError, IndexError) as error:
            raise ValueError(f"--move expects COL,ROW,X,Y (x/y 0..1): {text!r}") from error
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(args.image).stem
    uvgrid.draw_overlay(image, grid).save(out / f"{stem}_grid.png")
    uvgrid.flatten(image, grid).save(out / f"{stem}_flat.png")
    (out / f"{stem}_grid.obj").write_text(grid.to_obj(stem), encoding="utf-8")
    (out / f"{stem}_grid.json").write_text(grid.to_json(image.size), encoding="utf-8")
    print(f"UV grid {grid.cols}x{grid.rows}: wrote {stem}_grid.png, _flat.png, _grid.obj, _grid.json to {out}")
    return 0


def cmd_face14(args, ws: Workspace) -> int:
    """Put a 2K14 (or any) face diffuse - DDS / PNG, alpha = hair coverage - into a 2K20 cyberface IFF."""
    import tempfile

    from nba2k20 import convert14

    ws.open_iff(args.file)
    texture = next((t for t in ws.opened.textures if t.number == args.texture), None)
    if texture is None:
        raise ValueError(f"texture {args.texture} not found; use: python cli.py iff list {args.file}")
    img = convert14.fit_face_texture(convert14.load_face_image(args.face), (texture.width, texture.height))
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "face.png"
        img.save(png)
        change = ws.import_texture(args.texture, png)
    save = ws.save_iff(args.output, allow_overwrite=args.force)
    _dump({"face": str(args.face), "size": [texture.width, texture.height], "change": change, "save": save})
    return 0


def cmd_iff14(args, ws: Workspace) -> int:
    """Read the face texture out of a 2K14 cyberface IFF and save it as PNG."""
    from nba2k20 import iff14

    image, info = iff14.read_face(args.file)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    info["output"] = str(args.output)
    _dump(info)
    return 0


def cmd_objfix(args, ws=None) -> int:
    from nba2k20 import meshfix
    text = Path(args.file).read_text(encoding="utf-8", errors="replace")
    fixed, rep = meshfix.fix_obj_text(text, smooth_strength=args.smooth)
    Path(args.output).write_text(fixed, encoding="utf-8")
    print(meshfix.report_text(rep))
    print(f"wrote {args.output}")
    return 0


def cmd_port14(args, ws: Workspace) -> int:
    """One-tap 2K14 -> 2K20 port onto the built-in (or your own) 2K20 base; many files / a whole folder at once."""
    from nba2k20 import port14

    sources: list[Path] = []
    for item in args.source:
        item = Path(item)
        sources += port14.find_sources(item) if item.is_dir() else [item]
    if not sources:
        raise ValueError("no source files found")
    options = port14.PortOptions(head_shape=not args.no_head, head_obj=args.head_obj, even_brows=args.brows,
                                 tint=args.tint, align=not args.no_align, strength=args.strength,
                                 make_lods=not args.no_lods, body_iff=args.body)
    try:
        result = port14.port_batch(sources, args.out, args.base, options,
                                   progress=lambda i, n, name: print(f"[{i}/{n}] {name}", file=sys.stderr))
    except port14.PortError as error:
        raise ValueError(str(error)) from error
    _dump({"summary": result.summary, "done": result.done, "failed": result.failed})
    return 1 if result.failed and not result.done else 0


def cmd_shapefit(args, ws: Workspace) -> int:
    """Move a 2K20 head OBJ toward the shape of another head OBJ (vertex count / UV / faces unchanged)."""
    from nba2k20 import convert14

    report = convert14.shape_fit_files(args.target, args.source, args.output, strength=args.strength,
                                       smooth=args.smooth, scale=args.scale, dx=args.dx, dy=args.dy, dz=args.dz)
    _dump(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    groups = parser.add_subparsers(dest="group", required=True)

    iff = groups.add_parser("iff", help="work on a loose .IFF file").add_subparsers(dest="cmd", required=True)
    p = iff.add_parser("list", help="show textures / summary")
    p.add_argument("file", type=Path)
    p.add_argument("--full", action="store_true", help="full JSON incl. every resource")
    p.set_defaults(func=cmd_iff_list)
    p = iff.add_parser("export-png", help="export every texture as PNG")
    p.add_argument("file", type=Path)
    p.add_argument("folder", type=Path)
    p.set_defaults(func=cmd_iff_export_png)
    p = iff.add_parser("export-resources", help="export every resource / raw region")
    p.add_argument("file", type=Path)
    p.add_argument("folder", type=Path)
    p.set_defaults(func=cmd_iff_export_resources)
    p = iff.add_parser("replace", help="replace textures by number and save a new IFF")
    p.add_argument("file", type=Path)
    p.add_argument("--texture", action="append", nargs=2, metavar=("NUMBER", "PNG"), required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--force", action="store_true", help="allow overwriting the source IFF")
    p.set_defaults(func=_iff_apply_and_save)
    p = iff.add_parser("replace-folder", help="import every PNG that matches an exported name")
    p.add_argument("file", type=Path)
    p.add_argument("folder", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=_iff_apply_and_save)
    p = iff.add_parser("scan", help="list every IFF in a folder")
    p.add_argument("folder", type=Path)
    p.set_defaults(func=cmd_iff_scan)
    p = iff.add_parser("catalog", help="build the searchable all-IFF catalog (SQLite)")
    p.add_argument("folder", type=Path)
    p.set_defaults(func=cmd_iff_catalog)

    obb = groups.add_parser("obb", help="work directly on a main/patch .obb").add_subparsers(dest="cmd", required=True)
    p = obb.add_parser("list", help="list editable IFF entries")
    p.add_argument("obb", type=Path)
    p.add_argument("--search", help="entry number, name, hash or type")
    p.add_argument("--all", action="store_true", help="include non-IFF entries (CDF, OGG, ...)")
    p.set_defaults(func=cmd_obb_list)
    p = obb.add_parser("unknown", help="report entries with unknown file names (hash + block sizes)")
    p.add_argument("obb", type=Path)
    p.add_argument("--output", "-o", type=Path, help="write the CSV here")
    p.set_defaults(func=cmd_obb_unknown)
    p = obb.add_parser("textures", help="list the textures of one entry")
    p.add_argument("obb", type=Path)
    p.add_argument("index", type=int)
    p.set_defaults(func=cmd_obb_textures)
    p = obb.add_parser("export-png", help="export all textures of one entry")
    p.add_argument("obb", type=Path)
    p.add_argument("index", type=int)
    p.add_argument("folder", type=Path)
    p.set_defaults(func=cmd_obb_export_png)
    p = obb.add_parser("export-iff", help="export one complete IFF entry")
    p.add_argument("obb", type=Path)
    p.add_argument("index", type=int)
    p.add_argument("destination", type=Path, help="folder, or a file named exactly like the entry")
    p.set_defaults(func=cmd_obb_export_iff)
    p = obb.add_parser("import-iff", help="replace one entry with a complete IFF and write a new OBB")
    p.add_argument("obb", type=Path)
    p.add_argument("index", type=int)
    p.add_argument("file", type=Path, help="the IFF to import (decompressed size must match)")
    p.add_argument("output", type=Path)
    p.add_argument("--force", action="store_true", help="allow overwriting an existing output")
    p.set_defaults(func=cmd_obb_import_iff)
    p = obb.add_parser("patch", help="edit several entries and write a verified new OBB")
    p.add_argument("obb", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--png", action="append", metavar="INDEX:FOLDER", help="import PNGs for an entry")
    p.add_argument("--iff", action="append", metavar="INDEX:FILE", help="replace an entry with a complete IFF")
    p.add_argument("--force", action="store_true", help="allow overwriting an existing output (or the source)")
    p.set_defaults(func=cmd_obb_patch)
    uv = groups.add_parser("uv", help="UV grid maker: grid over an image -> OBJ / JSON / flattened PNG")
    uv.add_argument("image")
    uv.add_argument("output", help="folder for the result files")
    uv.add_argument("--grid", default="12x12", help="cells, e.g. 12x12 (default)")
    uv.add_argument("--load", metavar="JSON", help="start from a saved grid JSON")
    uv.add_argument("--move", action="append", metavar="COL,ROW,X,Y", help="move one point (x/y 0..1); repeatable")
    uv.set_defaults(func=cmd_uv)

    f14 = groups.add_parser("face14", help="2K14 face texture (DDS/PNG) -> texture of a 2K20 cyberface IFF")
    f14.add_argument("file", type=Path, help="2K20 cyberface .iff")
    f14.add_argument("face", type=Path, help="face diffuse .dds / .png (alpha = hair coverage)")
    f14.add_argument("--texture", type=int, default=1, help="texture number to replace (default 1 = FACE DIFFUSE)")
    f14.add_argument("--output", type=Path, required=True)
    f14.add_argument("--force", action="store_true", help="allow overwriting the source IFF")
    f14.set_defaults(func=cmd_face14)

    i14 = groups.add_parser("iff14", help="2K14 cyberface .iff -> face texture PNG")
    i14.add_argument("file", type=Path, help="2K14 cyberface .iff (png####.iff)")
    i14.add_argument("--output", type=Path, required=True, help="PNG to write")
    i14.set_defaults(func=cmd_iff14)

    of = groups.add_parser("objfix", help="repair a head OBJ: weld cracks, fix inside-out faces, remove spikes, smooth")
    of.add_argument("file", type=Path, help="head .obj to repair")
    of.add_argument("--output", type=Path, required=True)
    of.add_argument("--smooth", type=float, default=0.35, help="0..1 smoothing strength (default 0.35, 0 = off)")
    of.set_defaults(func=cmd_objfix)

    p14 = groups.add_parser("port14", help="ONE-TAP 2K14 -> 2K20 port onto the built-in (or your own) 2K20 base")
    p14.add_argument("source", nargs="+", type=Path, help="2K14 png####.iff / DDS / PNG, or a folder of them")
    p14.add_argument("--out", type=Path, required=True, help="output folder (result keeps the source's name)")
    p14.add_argument("--base", type=Path, default=None, help="your own 2K20 base IFF (default: the built-in base)")
    p14.add_argument("--no-head", action="store_true", help="texture only: keep the base head shape")
    p14.add_argument("--head-obj", type=Path, default=None, help="a 2K14 head OBJ (default: the one inside the IFF)")
    p14.add_argument("--brows", action="store_true", help="even brows + right brow / eye repair")
    p14.add_argument("--tint", type=int, default=0, choices=(0, 1, 2, 3), help="face skin tint: 0 none .. 3 darkest")
    p14.add_argument("--no-align", action="store_true", help="do not line the face up with the base's face map")
    p14.add_argument("--strength", type=float, default=1.0, help="head shape strength 0..1")
    p14.add_argument("--no-lods", action="store_true", help="skip the LOD textures")
    p14.add_argument("--body", type=Path, default=None, help="body IFF whose skin tone follows the new face")
    p14.set_defaults(func=cmd_port14)

    sf = groups.add_parser("shapefit", help="fit a 2K20 head OBJ to the shape of another head OBJ")
    sf.add_argument("target", type=Path, help="2K20 head OBJ (e.g. assets/head_default.obj) - topology is kept")
    sf.add_argument("source", type=Path, help="head OBJ whose shape you want (e.g. HEADKD.obj)")
    sf.add_argument("--output", type=Path, required=True)
    sf.add_argument("--strength", type=float, default=1.0, help="0..1 how far to move (default 1)")
    sf.add_argument("--smooth", type=int, default=2, help="smoothing passes (default 2)")
    sf.add_argument("--scale", type=float, default=1.0, help="extra scale of the source (default 1)")
    sf.add_argument("--dx", type=float, default=0.0)
    sf.add_argument("--dy", type=float, default=0.0)
    sf.add_argument("--dz", type=float, default=0.0)
    sf.set_defaults(func=cmd_shapefit)

    sc = groups.add_parser("scene", help="court / arena / scoreboard SCNE (PC-style IFF or .SCNE) <-> OBJ").add_subparsers(
        dest="cmd", required=True)
    p = sc.add_parser("list", help="list the geometry models")
    p.add_argument("file", type=Path)
    p.set_defaults(func=cmd_scene)
    p = sc.add_parser("objects", help="list placed Objects (name, target, x y z); --grep score / board / hoop ...")
    p.add_argument("file", type=Path)
    p.add_argument("--grep", default="", help="regex on object / target name")
    p.add_argument("--limit", type=int, default=0)
    p.set_defaults(func=cmd_scene)
    p = sc.add_parser("move", help="move ONE placed Object (game axes, Y = up) into a NEW copy")
    p.add_argument("file", type=Path)
    p.add_argument("name", help="Object name from 'scene objects'")
    p.add_argument("--dx", type=float, default=0.0)
    p.add_argument("--dy", type=float, default=0.0)
    p.add_argument("--dz", type=float, default=0.0)
    p.add_argument("--absolute", action="store_true", help="dx/dy/dz are the new position, not an offset")
    p.add_argument("--scne", default="", help="SCNE file name when the name exists in several")
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(func=cmd_scene)
    p = sc.add_parser("export-obj", help="export every model to one OBJ")
    p.add_argument("file", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(func=cmd_scene)
    p = sc.add_parser("import-obj", help="write an edited OBJ back into a NEW copy (vertex count / order must not change)")
    p.add_argument("file", type=Path)
    p.add_argument("obj", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--no-uv", action="store_true", help="positions only")
    p.set_defaults(func=cmd_scene)

    sb = groups.add_parser("scoreboard", help="scoreboard layout (newscorebug.iff): list / move elements").add_subparsers(
        dest="cmd", required=True)
    p = sb.add_parser("list", help="list the layout items: index, name, x, y, size, scale")
    p.add_argument("file", type=Path)
    p.set_defaults(func=cmd_scoreboard)
    p = sb.add_parser("move", help="change x / y / size / scale of one item and save a NEW file")
    p.add_argument("file", type=Path)
    p.add_argument("item", type=int, help="item index from 'scoreboard list'")
    p.add_argument("--x", type=float)
    p.add_argument("--y", type=float)
    p.add_argument("--size", type=float)
    p.add_argument("--scale", type=float, help="plain 0x120 nodes only")
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(func=cmd_scoreboard)

    return parser


def cmd_scoreboard(args, ws) -> int:
    from nba2k20 import scorelayout as sl
    opened = core.open_iff(args.file)
    items = sl.find_items(opened.data)
    if not items:
        raise ValueError("Walang nakitang layout node sa file na ito.")
    if args.cmd == "list":
        _dump([{k: (round(v, 3) if isinstance(v, float) else v) for k, v in i.items() if k != "offset"} for i in items])
        return 0
    if not 0 <= args.item < len(items):
        raise ValueError(f"item {args.item} does not exist (0 - {len(items) - 1})")
    if all(v is None for v in (args.x, args.y, args.size, args.scale)):
        raise ValueError("Maglagay ng kahit isang: --x --y --size --scale")
    item = items[args.item]
    if item.get("kind") == "obj":
        mirrors = sl.pair_mirrors(opened.data, items)
        if args.x is not None or args.y is not None:
            sl.set_item_xy(opened.data, item, item["x"] if args.x is None else args.x,
                           item["y"] if args.y is None else args.y, mirrors)
        if args.size is not None:
            sl.set_item_size(opened.data, item, args.size, mirrors)
    else:
        changes = {k: v for k, v in (("x", args.x), ("y", args.y), ("size", args.size), ("scale", args.scale)) if v is not None}
        sl.set_node(opened.data, args.item, **changes)
    _dump(core.save_iff(opened, args.output, allow_overwrite=True))
    return 0


def cmd_scene(args, ws) -> int:
    from nba2k20 import scenetool
    if args.cmd == "list":
        _dump(scenetool.list_models(args.file))
    elif args.cmd == "objects":
        _dump(scenetool.list_objects(args.file, args.grep, args.limit))
    elif args.cmd == "move":
        _dump(scenetool.move_object(args.file, args.name, args.output, args.dx, args.dy, args.dz, args.absolute, args.scne))
    elif args.cmd == "export-obj":
        _dump(scenetool.export_obj(args.file, args.output))
    else:
        _dump(scenetool.import_obj(args.file, args.obj, args.output, uv=not args.no_uv))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ws = Workspace()
    try:
        return args.func(args, ws)
    finally:
        ws.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, WorkspaceError, zlib.error) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
