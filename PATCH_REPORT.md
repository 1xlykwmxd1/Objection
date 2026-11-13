# David2k Tool v148 — Patch report

## Mga fix mula sa `allinfo.zip`

Ang JSON para sa `english.iff` ay naglista ng 129 texture descriptor ngunit 0 decodable dahil buong alias groups (116 at 13 descriptors) ay tinatakan ng runtime kahit ang sample allocations ay 262,144 at 1,048,576 bytes at kasya sa encoded payload sizes. Inalis ang blanket rule: ang shared alias ay pinananatiling decodable lamang kung may sapat na allocation at ang buong byte span ay nasa loob ng IFF file. Ang location ay nagsasaad na shared ang payload dahil ang edit sa isang alias ay makakaapekto sa lahat ng descriptor na tumuturo roon.

Ang `gamedataextra.iff` JSON ay may 170 descriptors, pero sample allocations ay 24 bytes samantalang 8,192–65,536 bytes ang hinihingi. Nanatiling blocked ang mga ito dahil walang kumpletong pixels sa slot na iyon; nag-uulat na ang error ng available at required byte count. Ang `crowd.iff` ay may isang 128×128 ETC2 RGBA8 descriptor, pero sinasabi ng JSON na ang bytes pagkatapos ng header ay isa pang descriptor at wala itong payload offset. Hindi ito kino-decode bilang larawan para maiwasan ang garbage preview.

## Title Card

Pinalawak ang hash names para sa karaniwang `titlecard`, `title_card`, `titlecardbg`, `titlecardbackground`, `titlecardoverlay`, `titlepage`, at `titlescreen` variants. Ang `titlecard` ay inilagay sa **Title Page** category; ang overlay ay **Frontend**. Gumagana na ang space-insensitive search kaya ang query na `title card` ay tumutugma rin sa `titlecard.iff`.

Gayunman, walang `titlecard` record o OBB filename/hash listing sa `allinfo.zip`—ang laman nito ay JSON diagnostics lang para sa tatlong ibang IFF. Kaya hindi pa matitiyak kung may hiwalay na title-card entry sa mismong `main.obb`/`patch.obb`, o kung ibang pangalan/hash ang gamit nito.

## Release at validation

- `nba2k20/version.py`: `VERSION_CODE=148`, `VERSION_NAME="v148"`.
- Lahat ng Buildozer specs: `version = 1.0.148`.
- `python3 -m compileall -q main.py cli.py nba2k20 tests` — pumasa.
- `python3 -m unittest discover -s tests -q` — **319 tests run; 318 passed, 1 skipped**. Ang isang skip ay nangangailangan ng tunay na game cyberface fixture.
- Naidagdag ang synthetic tests para sa bounded shared aliases, undersized slots, titlecard CRC aliases at Title Page category/search.
- Walang APK build o in-game visual check sa sandbox. Wala ring raw IFF/OBB bytes sa `allinfo.zip` para i-decode rito.

## Build / run

- CLI: `pip install -r requirements-termux.txt`; pagkatapos `python3 cli.py --help`.
- Recursive IFF scan: `python3 cli.py iff scan /path/to/extracted/game/resources`.
- Tests: `python3 -m unittest discover -s tests`.
- Android APK sa Linux/WSL: `pip install buildozer cython`, pagkatapos `buildozer android debug`; tingnan ang `BUILD.md` para sa Buildozer variants.
## v216 - CHIN GUARD (beard adjust no longer drags the chin)
- Problem: with BEARD locked, GRAB / MOVE pulled the chin / jaw skin along (the BEARD region is a geometric guess that includes the chin,
  and the one-point falloff covered ~45% of the part).
- Fix (render3d.py): `_guard_map()` holds the chin / jaw skin under the mouth (front, centre, upper part of the locked area) at 0 and fades
  it into the free lower part, applied in `_commit` so EVERY tool obeys it (Grab, Move, Smooth, Inflate, Flatten, Scale, Rotate, SIZE).
  FIX SHAPE / ERASER can still return vertices to the original shape.
- New buttons (sculptkit.py): CHIN GUARD ON/OFF, PROTECT SEL (freeze selected vertices by hand), CLEAR PROTECT.
- Tests: tests/test_v216_chin_guard.py. Full suite: 564 tests OK. Version bumped to v216 (version.py + 3 buildozer specs).
- v216 (2): EXACT BEARD. In a full native head OBJ (3168 verts, or any OBJ with a `g ...beard...` group) the beard hair is its own vertex
  block (2922..3167, canonical 'Beard' group) with no vertex shared with the face skin. `Renderer._exact_beard()` now locks exactly that
  block for BEARD, so the chin cannot move at all. Head-only OBJs (beard sculpted into the skin, e.g. assets/heads/New Beard LBj.obj,
  1529 verts) keep the CHIN GUARD fallback. Tests: tests/test_v216_exact_beard.py. Full suite 566 OK.

## v217 - UV tools + filter (written from scratch, Python)
- uvedit.py: mirror() [MIRROR U / V across 0.5], islands(), pack() [PACK 0-1: shelf-packs every UV island into 0..1, one shared scale].
- render3d.py: project_uv("cylindrical") [CYLINDRICAL UNWRAP], reset_uv() [RESET UV back to the OBJ's own UVs].
- uvfull.py: buttons CYLINDRICAL UNWRAP, MIRROR U, MIRROR V, PACK 0-1, RESET UV, HISTORY (last ops log), FRAME ALL.
- filters.py + sculptkit.py: SCANLINES toggle next to VIGNETTE.
- Tests: tests/test_v217_uv_tools.py. Full suite 571 OK.

## v221
- team_sync: NAME GUARD - ratings/age/position are only written to a slot that really carries the target player's name (a slot that kept the old name, e.g. Trier/Prince/Shayok, no longer gets LeBron/Brown/Maxey data). Reported in "Problems".
- FULL AUTO + portraits: opens the last-used patch OBB by itself (asks once if none), stages every new face, saves a verified copy to patched_obb/.
- OBB open speed: the saved OBB inherits the name + classification caches (new size/mtime used to invalidate them, so every re-open redid the slow scan).
- Not measured on a real OBB / phone (none available here). Save is still one full copy pass; true in-place patching is NOT implemented.
- roster_core.setName: a name rewritten in place now clears that part's name CRC (it kept the old player's CRC, and the game showed the old name). New optional arg clear_crc=True clears both. Evidence: in the user's edited ROS the renamed slots with stale CRC showed the old names in-game (Trier/Prince/...), while Edwards and Hukporti (CRC 0) showed correctly. NOT confirmed in-game yet.
- iff_core.auto_decode_image: when the descriptor's size/format reads as noise, the SAME bytes are tried as RGBA8888 / RGB565 / RGBA4444 / RG88 / L8 / ETC2 RGBA8 / ETC2 RGB at every power-of-two size that uses exactly that many bytes; the clearly smooth one is shown (preview only, export/import unchanged). Tested on a synthetic mislabeled texture; NOT tested on the real F021.IFF (not provided).
