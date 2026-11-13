# v249 - ano ang bago

1. MESH TOOL (home card): split 50/50 (3D | texture), menu bar (Texture, View, Sculpt, Transfer, Soft Mod, UV, Camera, Export, =),
   bottom bar (Split 50/50 / 3D Model / Texture / Cam lock / Rotate / Options). Walang swipe rows.
   - nba2k20/meshxfer.py: numpy port ng MeshDataTransfer (closest / raycast / UV-space, snap, mask, blend) at softMod (falloffs, surface-only, symmetry).
   - nba2k20/meshtool.py: Transfer + Soft Mod menus / panel. nba2k20/menukit.py + menuspec.py: ang menu bar.
2. CYBERFACE EDITOR / OBJ at ang Open-IFF editor ay gumagamit na rin ng menu bar (lahat ng lumang tools ay nasa menus; ang hindi kilala ay nasa Menu "=" > More tools).
3. 2K14 -> 2K20 PORT: bagong menu (source, target, optional BODY IFF, AUTO _HI/_LO). Hinahanap ang _hi/_lo/body siblings (kahit ibang case / zero-pad / sub-folder);
   ang target _hi/_lo na walang source counterpart ay tumatanggap ng main ng source (hindi bumabalik ang lumang mukha); kung wala talagang _hi/_lo, ginagawa mula sa main;
   body skin tone ay na-ma-match sa mukha. May "notes" sa result na nagsasabi kung ano ang kulang.
Hindi pa na-test sa tunay na game files / Kivy / phone.
4. GPU VIEW: automatic ON pagbukas ng editor (tahimik na bumabalik sa Pillow renderer kung hindi kaya ng phone).
5. Mesh Tool: "★ Auto-UV" button sa menu bar, at "3D Hair" menu (Generate 3D beard / hair / braids mula sa built-in template).
6. OBJ editor: Sculpt > "DELETE selected vertices" para sa sobrang vertex ng port. IFF import hanggang 4096x4096 (mabagal ang malaki).

# v250
- png1316.iff: ang SKIN / FACE MAP ay grayscale detail map (kulay ay nasa png1316_hi.iff), kaya puti ang mukha. Preview na ngayon ay may skin tint
  (Texture menu > Preview skin tone). Preview lang - hindi isinusulat sa IFF.
- Hair color: isang tap sa swatch = buong hair (3D preview + scalp layer + buong HAIR / BACK OF HEAD texture ng IFF). NATURAL COLOR = ibalik.
- Bug fix: hindi nakikilala ang HAIR / BACK OF HEAD texture kapag walang "HI" prefix (png1316) kaya pumapalya ang import/export hair.

## v251
- Cyberface Editor: kapag walang napiling texture o ang HAIR (1 MB) ang napili, awtomatikong FACE / SKIN map ang bubuksan (hindi ang buhok).
- Menu bar: "▾" (kahon sa ibang phone) -> "v".
- 3D beard: SHELL (tuloy-tuloy na surface) ang default; tinest sa png1316.iff at pngNNN_EDITED_lo.iff (generate + save + reopen).

## v252
- Textures tab: ang grey SKIN / FACE MAP ng 1 MB cyberface ay may preview na kulay balat (preview lang), hindi na puti/blangko.

## v253  (ang tunay na dahilan ng "1 MB hindi ma-edit")
- Ang 1 MB cyberface (png8007 / png8152 / png1316 / pngNNN ...) ay may 5 texture na 512 (face 512, skin 512, normal 512, detail 128/256, hair 512),
  pero 256-face layout lang ang kilala ng tool -> 2 texture lang ang nakita (walang HI FACE DIFFUSE). Ngayon binabasa ang sukat sa descriptor mismo
  (iff_core._dynamic_cyberface_layouts).

## v254
- Cyberface Editor (3213 strand-card head): ang HEAD ay gumagamit na ng bundled native fixed UV (headhair._fixed_head_uvs) -> hindi na smeared ang mukha.
- Ang hair/beard cards ay naka-HIDE by default sa editor (iginuguhit sila gamit ang face texture kaya itim); View part > ALL para ipakita.
- UV view: hindi na iginuguhit ang hidden faces.

## v255
- Editor (card heads): tinatago rin ang extra hair-cap faces (band sa noo) -> malinis na mukha tulad ng head-only render.

## v256
- Bug fix: sa v255 nabasag ng hide-code ang cyber editor object (variable `c`) -> hindi na-hide ang cards at nanatiling sira ang itsura. Naayos + test.

## v257
- Header ng editor ay may bersyon ("CYBERFACE EDITOR v257") para makumpirma kung tama ang na-install na build.
- Menu button na "☰" (kahon sa phone) -> "MORE".

## v258
- Release identity: package.name=pro, package.domain=com.david2ktool, version=2.0 (App ID: com.david2ktool.pro). In-app build = v258.

## v259
- Hide ng cards/shell/hair-cap sa editor ay para sa lahat ng packed head na may extra geometry (pati pagkatapos ng GENERATE 3D beard).

## v260
- 3D Hair menu: "SHOW 3D beard / hair here" (kita ang generated beard/hair/braids sa editor, GRAB tool agad) at "HIDE" (malinis na mukha).

## v261
- Menu buttons: tap opens an accordion drawer on the LEFT; tap the same button again closes it.
- GPU view: while dragging, skips the UV picture and (dense meshes) wire/lock lines; shorter frame gap.

## v262
- 3D beard/hair cards in the GPU view use the HAIR / BACK OF HEAD map (alpha-cut) via a face+hair atlas, not the flat face map.

## v263
- Any strand-card head stream (png1253 = 2859 = head + 414 beard cards) opens with its 3D beard (hidden by default; SHOW 3D beard), hair strand map tinted like the game.

## v264
- 2K14 PORT: a 2K14 .iff now brings its OWN head mesh (first 2445 stream records) for SHAPE FIT; no png####.obj needed.

## v265
- 2K14 PORT: no 2K20 target needed (built-in base), FACE SKIN TINT OFF/1/2/3.

## v266
- GPU view auto-shows the 3D beard / hair cards (hair map + alpha) when the file has cards and a hair map.

## v267
- 2K14 PORT: TEXTURE SIZE NATIVE 512 / HIGH 1024 (bundled 1024 base), EXPORT AS ZIP.

## v268
- 2K14 PORT defaults to HIGH base = complete HI + LO2 + LO set (13 textures). convert14.reproject_texture added (UV rebake; 2K14 UV decode still unsolved, not wired in).

## v269
- 2K14 PORT: the 2K14 face is auto-aligned (x/y scale + shift, numpy FFT) to the 2K20 base face map before import.

## v270
- Menu: ALL buttons are one tall column on the LEFT; the pressed one grows open under itself (accordion), press again closes.
- Android edge-to-edge (display cut-out short edges + immersive) for the black strips.

## v271
- HIGH base of the 2K14 port = neutral reference tool-structure base (same 2859 head + beard cards for everybody; only the face maps differ), not Lamelo-specific.

## v272
- 3D Hair menu: ADD / SHOW 3D beard + 1-tap BEARD LONGER / SHORTER / WIDER / NARROWER / THICKER / THINNER (undo works).

## v273
- 3D Hair > GENERATE 3D beard now works on the OPEN IFF (was: built-in 3213 template = other face / 3205 vertices). Old top menu bar removed (it overlapped the header).

## v274
- editor GENERATE 3D beard: no fallback to the built-in template IFF any more (message instead).

## v275 - 2K14 port now matches reference tool numerically
Measured on the real Wemby + Curry 2K14 files and reference tool's outputs:
- All 12 non-face textures (skin map, detail, normal, hair, LO/LO2) are byte-identical to reference tool's (same built-in base).
- reference tool darkens the face by a constant x0.875 (its "Fixed Skintone"); FACE SKIN TINT "3 - DAVID AUTO" = 0.875, default.
- reference tool only stretches the face vertically (sx = 1); `align_to_reference` now searches sy / shift with a larger window.
- Result vs reference tool face HI: mean abs diff 1.94 / 255 for both Wemby and Curry (was 9.7 / 16.8).

## v276
EVEN BROWS option in 2K14 PORT (convert14.even_brows). Measured: face map symmetry axis is already centred (0 px) and L/R brow correlation equals reference tool, so the uneven brow comes from the source face; the option mirror-blends the brow band.

## v277
- iff_core.decompress_wrapper: ZLIB blocks whose declared stored size is a few bytes too long (png1603_retex, 21 MB VRAM block) no longer drop the next block; such files now open with all textures.
- 2K14 PORT: AUTO _HI/_LO files default OFF (the main file already holds HI+LO+LO2; fewer GB, one output file like reference tool).

## v278
- GENERATE 3D BEARD default shape = "cards" (the real curly strand map of the file, mouth stays free). The old "shell" painted one solid black silhouette over the atlas = the flat mask over the mouth / chin.
- Pillow / CPU view draws strand cards from the tinted hair map with alpha (render3d card_tex) instead of the face texture; draft view uses the hair colour.

## v278 notes - 2K14 UV findings (no code change)
- 2K14 SD-leg IFF (Wemby, Curry): per-vertex UV = int16 pairs, stride 28, at decompressed offset 708144 (second copy 879504); u = x/32767, v = 1 - y/32767; first 1700 vertices (face) equal the 2K20 head UV EXACTLY, for both players.
- Their 3D head stream is identical too (same extents / centre), so reference tool has no geometry or UV difference to transfer for these files; its Curry result is a global vertical stretch (image fit). convert14.align_to_reference reproduces it (mean abs diff 1.9/255).

## v279
- Removed the reference tool name from the UI (tint level is now "3 - DAVID AUTO"); EVEN BROWS defaults to ON in the 2K14 port.

## v280
- Saves keep each block slot at its ORIGINAL size (zero padded), which is why a 1 MB cyberface stayed 1.25 MB. New iff_core.save_iff(compact=True) / rebuild_compressed_iff(compact=True) drops the padding; the 2K14 port uses it (button COMPACT FILE, default ON). png1603 port: 1.25 MB -> 0.66 MB (the two reference tools give 0.70-0.74 MB). Needs an in-game test.

## v281 - ONLINE PACK
- assets/license.json: pack_url / pack_grace_hours / pack_required. After the key login the app downloads the zip from your panel; deleting the zip there (or 401/403/404/410) wipes the app copy and login is refused = online access. See nba2k20/packs.py + tools/make_pack.py. Data files only; code is never downloaded.
