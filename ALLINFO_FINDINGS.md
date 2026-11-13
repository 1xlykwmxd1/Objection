# Findings from `allinfo.zip` diagnostics

Ang ZIP ay may JSON diagnostics para sa `crowd.iff`, `english.iff`, at `gamedataextra.iff`; wala itong raw `.iff` bytes, OBB entry list, o `titlecard.iff` record.

| File | Nasa diagnostic | Kahulugan / aksyon sa v148 |
|---|---|---|
| `crowd.iff` | 1 texture; format 16 (ETC2 RGBA8), 128×128, 16,384-byte payload, pero `payload_offset=null`. Sinasabi ng parser na ang bytes pagkaraan ng header ay isa pang descriptor. | Hindi ligtas i-decode ang descriptor bytes bilang pixels. Nananatiling blocked hanggang may tunay na pixel span o katumbas na external texture file na ma-verify. |
| `english.iff` | 129 descriptors, 0 na iniulat na decodable ng v147. Ang 116-item at 13-item groups ay nagtuturo sa parehong physical slots; sample allocations na 262,144 at 1,048,576 bytes ay kasya sa kani-kanilang required payloads. | Masyadong agresibo ang v147 blanket “shared = no pixels” rule. Sa v148, pinananatiling previewable ang alias kung may buong bounded payload sa loob ng file; may “shared payload” note ang location dahil ang edit ay tumatama sa lahat ng aliases. |
| `gamedataextra.iff` | 170 descriptors, 0 decodable. Shared groups na 50 at 120; sample slot ay 24 bytes lamang samantalang 8,192–65,536 bytes ang kailangan. | Kulang ang bytes sa record na iyon para makabuo ng image. Tama ang fail-closed behavior; malamang nasa ibang resource/stream ang pixels, at wala sa ZIP ang source data para resolbahin ito. |

## Title Card search

Walang title-card record sa tatlong JSON. Sa v148, pinalawak ang OBB CRC name candidates para sa `titlecard`, `title_card`, `titlecardbg`, `titlecardbackground`, at `titlecardoverlay` variants; ang `titlecard` ay kabilang sa **Title Page** category. Search queries gaya ng `title card` ay kino-normalize kaya puwedeng tumugma sa `titlecard.iff`.

Hindi pa mapapatunayan kung may hiwalay na title-card entry sa partikular na `main.obb` o `patch.obb`, o kung ibang hash/name ang ginagamit. Kailangan ang OBB file o OBB entry listing (index + hash/label) para matukoy ang eksaktong entry; ang `allinfo.zip` na ito ay walang ganoong listahan.
## v233 - GENERATE 3D BEARD: no more 8-card limit
- Cause: the beard generator only used the spare card vertices of the IFF (PNG1013: 51 vertices = 8 cards). The 320 vertices / index entries
  of the OLD beard were only collapsed, never reused.
- Fix (headhair.py): `compact_index()` cuts the old beard (and the hair when the atlas is taken over) out of the strip index buffer, so its
  vertices and entries go back to the pool. PNG1013: 8 -> 61 cards. Head strips and every other card are byte-identical in triangle set / winding.
- Fix (beardgen.py `strip_entries`): bridges now always repeat the first vertex twice; before, an odd start left a stray triangle from the previous
  strip's last vertex to the new card.
- Tests: tests/test_v232_beardgen.py (compact_index test; "new triangle" check now uses the freed vertices). Full suite: 4 failures, all pre-existing
  (test_v218 transfer_beard, test_sync_options body_off, 2 x test_workshop_ui AudioReplaceSave).
- Not verified in the game.

## v234 - GENERATE 3D HAIR / BRAIDS, AUTO KAPAL, GAMITIN LAHAT NG SLOTS
- beardgen.BeardParams: `kind` ("beard" | "hair" | "braids"), `take_hair` (the other cards give way: PNG1013 beard 61 -> 127 cards), `auto_thick` (fewer
  cards than asked -> every card wider, up to x2.2, so the coverage stays).
- hair_weights() = scalp without forehead / ears; braid_weights() = back of the head; make_braid_tile() = 5 plaits (one plait per card).
- headhair._beard_analysis(..., drop=("BEARD",) / ("HAIR",) / both) removes the replaced cards from the index buffer (v233 compact_index).
- main.py: BEARD / HAIR / BRAIDS buttons + GAMITIN LAHAT NG SLOTS toggle in the generator dialog (UI not run headless; only compiled).
- Not verified in the game.

## v235 - generated cards use the file's REAL strand patches (no more solid blocks)
- Problem (in-game screenshot): v232-v234 painted a self-made strand picture over a 256x256 part of the strand atlas (also over braid / hair
  patches of other cards) and the cards were 2-3x longer than the template's own, so the beard looked like opaque dark chunks.
- Fix: `headhair._uv_windows()` reads the strand patches (u_left, u_right, v_root, v_tip) of the template's own cards (beard / short hair / long
  braids). New cards show those patches; the atlas is NOT painted over (only recoloured inside the used patches when a lighter colour is picked).
  Cards are smaller and overlap; braid cards take the aspect of their braid patch. `BeardParams.generated_tile=True` keeps the old tile painter.
- Not verified in the game.

## v236 - denser 3D beard + dark base painted into the face texture
- `segment_choice(..., dense)`: when 2-segment cards cannot give the wanted number, 1-segment quads (4 vertices) are used (PNG1013: 61 -> 92 cards
  replacing the beard only, 127 -> 190 with GAMITIN LAHAT NG SLOTS). `MAX_CARDS` 150 -> 190.
- `beardgen.paint_base()` / `uv_weight_map()`: a soft dark stubble layer follows the beard weight map in the face-texture UV layout (UV v is
  flipped: checked on the SKIN / FACE MAP of PNG1013). Painted into FACE DIFFUSE (else SKIN / FACE MAP) textures only for kind "beard", always from
  the original picture; RESET or another kind restores it. Alpha channel untouched.
- UI toggle PINTURA SA MUKHA. Not verified in the game.
