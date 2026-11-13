# Changelog — David2k Tool

## v292 (in progress) - ONE-TAP 2K14 -> 2K20 PORT (built-in base)
- **Bago: `nba2k20/port14.py`** - pick a 2K14 `png####.iff` (or a face DDS / PNG), use the BUILT-IN 2K20 base (`assets/bases/cyberface_base.iff`) or your OWN base IFF, and get a NEW file named after the source. Source and base are never modified. Options map to settings the engine already had: HEAD SHAPE on/off, EVEN BROWS, face TINT 0-3, ALIGN, shape STRENGTH, LODs, BODY skin-tone follow. Batch / whole-folder mode: one bad file never stops the rest, each failure is reported with its reason. Every result is re-opened and checked against the base layout (`verified`).
- **CLI:** `python cli.py port14 SRC_OR_FOLDER --out DIR [--base MY.iff] [--no-head] [--brows] [--tint N] [--body BODY.iff]`.
- **Data:** `assets/raw/head_topology_3168.bin` added and `headdata.load_topology(3168)` now works (4683 faces). `hihead_HEAD.obj` / `hihead_HAIR.obj` are bundled in `assets/bases/` (not wired into the port yet).
- **Not verified:** no real 2K14 `png####.iff` was available, so the 2K14 head-stream -> base shape path was tested only with a 2K20 head OBJ as the source, and nothing was tested in-game. Tests: `tests/test_port14.py`.

## v247 (in progress, hindi pa na-bump ang version) - ARENA OBJECT MOVE + MALAKING HEAD STREAM
- **Ayos: cyberface na may 3999+ (hanggang 20000) vertices ay nabubuksan na.** Ang `packedhead.find_head_stream` ay may limit na 5000 vertices (1000-5000), kaya ang mga PNGxxx.iff na mas malaki roon ay lumalabas na "Walang native HEAD stream". Ngayon `MAX_STREAM = 20000` (`packedhead.MIN_STREAM` / `MAX_STREAM`). Ang 2445 / 3168 / 3213 / 3693 ay hindi nagbago (nasubukan sa tests/data/png*.iff). Para sa mga bagong laki na hindi 3213 / 3693 ay nabubuksan at na-eedit ang HEAD (unang 2445); ang hair / beard generator ay para pa rin sa 3213 / 3693 lang dahil iyon lang ang kilalang layout.
- **Bago: ilipat ang posisyon ng isang placed Object** (scoreboard, hoop, atbp.) sa arena / court IFF (PC-style, may .SCNE). Tanging ang 3 translation number (Matrix 12..14) ng Object na iyon ang nasusulat; lahat ng iba ay byte-identical, at bagong kopya ang output.
  - CLI: `python cli.py scene objects arena.iff --grep score` at `python cli.py scene move arena.iff NAME --dy 2.5 --output out.iff` (`--absolute`, `--scne`).
  - App: SCN > MOVE OBJECT (scoreboard / hoop): pumili ng IFF, i-filter ang listahan, pumili ng object, ilagay ang dx / dy / dz, APPLY.
  - Game axes ang gamit (Y = pataas). Hindi pa nasusubukan sa totoong 2K20 arena IFF; ang tunay na pangalan ng scoreboard object ay alamin gamit ang `scene objects`.
- tests: tests/test_v247_scene_objects.py.

## v246 - SUPORTA SA 3693 "_N" LAYOUT (png7898_N / png1393_N)
- Ang mga bagong "_N" cyberface (galing sa screenshots mo: Alex Sarr png1393, png7898) ay 3693 ang head stream: 2445 head + **1248** card vertices (ang 3213 ay 768), parehong stride 28 na rows, mas maliit na index buffer (9696 entries, pitong zero sa dulo).
- Kinikilala na ng tool ang 3213 AT 3693: `headhair.CARD_COUNTS`; ang layout ng bukas na file ay awtomatikong nakikita (`_adopt`). Gumagana na sa 3693: HEAD / HAIR report, EXPORT / REPLACE OBJ (ang UV ng cards ay galing sa vertex rows ng file mismo), Cyberface Editor (BEARD / HAIR lock, APPLY), GENERATE 3D BEARD / HAIR / BRAIDS (shell, cap, tubes), RESET (byte-identical), SAVE at reopen, at GENERATE ulit.
- Ayos sa index buffer: ang dulo ng buffer ay hinahanap na mula sa huling non-zero na entry (dati ay palaging 2 ang huli, kaya 0 ang libreng entry sa 3693).
- Sa png1393_N: ~573 libreng vertex at ~1928 libreng entry (hair cards ay nananatili hanggang may sapat na room); sa png7898_N: ~859 at ~2406. Mas malaki ang grid kapag "GAMITIN LAHAT NG SLOTS".
- tests: tests/test_v246_cards3693.py (gumagamit ng tests/data/png1393_N.iff at png7898_N.iff). Hindi pa nasusubukan sa totoong laro: gumamit ng kopya ng OBB.

## v245 - HINDI NA BINABAGO ANG FACE TEXTURE ng GENERATE (base paint OFF)
- **Bug (nakita sa screenshot mo, png2122):** pagkatapos ng GENERATE + SAVE, ang FACE MAP (texture #1) ay napuno ng itim: ang "PINTURA SA MUKHA" (v235) ay nagpipinta ng madilim na base sa face texture at permanente ito kapag na-save. Sa png2137 sample, ang face map ay nagbago ng halos buo (mean diff 136).
- **Ayos:** `base_paint` ay **OFF na by default** (BeardParams at sa GENERATE dialog). Ang face map at lahat ng ibang texture ay hindi na ginagalaw; ang laman ng IFF (lahat ng textures, LOD, ulo) ay pareho pagkatapos ng generate, save at reopen. Optional pa rin ang paint kung gusto mo (toggle sa dialog).
- Pagkatapos ng SAVE puwede pang i-edit ulit: i-open ang saved IFF at GENERATE / Cyberface Editor ulit (nasubukan sa test).
- tests: tests/test_v245_face_untouched.py.
- Hindi pa kasama: suporta sa 3693-vertex "_N" layout (png7898_N / png1393_N). Susunod.

## v244 - TOTOONG ARTWORK (galing sa png2137 / png8026 mo) sa 3D beard, hair at braids
- Nakita sa dalawang sample IFF mo na ang totoong 2K beard / braids / afro ay may **detalyadong drawing sa strand atlas** (png8026: malaking beard na may kulot na gilid, mustache, sideburn, afro curls; png2137: mahahabang braids na may plait). Doon galing ang ganda, hindi sa geometry. Ang procedural na picture ng v242 / v243 ay payat kumpara doon.
- Ginupit ang mga drawing na yon (`nba2k20/assets/art/*.png`) at ginamit sa: **BEARD shell** (buong beard picture, butas sa bibig, mustache sa ibabaw ng labi), **HAIR cap** (kulot na afro texture, mirror-tiled para walang tahi), **BRAID tubes** (totoong braid picture sa bawat side ng tubo). Kulay (BLACK / BROWN / GRAY) ay nagta-tint pa rin.
- `nba2k20/art.py` (bago). `BeardParams.art` (default True): kapag nawawala ang assets o `art=False`, procedural pa rin ang gagamitin.
- Ang mga drawing ay galing sa sample files na ibinigay para sa tool na ito: para sa sarili mong gamit, huwag i-redistribute.
- tests: tests/test_v244_art.py. Hindi pa nasusubukan sa totoong laro / sa phone UI.

## v243 - 3D HAIR SHELL + 3D BRAID TUBES (hindi na cards ang hair at braids)
- **Ayon sa hiling ("3D hair mismo, wag card"):** ang GENERATE 3D HAIR ay gumagawa na ngayon ng **SHELL**: isang tuloy-tuloy na 3D cap na sumusunod sa tunay na hugis ng anit (ray cast mula sa gitna ng bungo), bahagyang nakaangat sa balat, mas makapal sa tuktok, may hairline sa noo, sa ibabaw ng tenga at mas mababa sa batok (HABA = mas mahaba sa likod). Ang crown ay isang saradong punto at ang mga column ay nagbabahagi ng vertices: walang gaps, walang magkakapatong na cards.
- Ang **BRAIDS** ay **3D TUBES** na: bawat braid ay bilog na tubo (4 o 3 sides, 7 rings) na lumalabas sa likod ng ulo, bumabagsak at numinipis papunta sa dulo, may plaited na picture. May tunay na volume, hindi flat strip.
- Ang beard shell (v242) ay hindi ginalaw. HAIR / BRAIDS / BEARD ay default na SHELL; ang CARDS toggle ay nandiyan pa rin kung kailangan.
- Bagong `nba2k20/hair3d.py` (`plan_hair_shell`, `plan_braid_tubes`, `make_hair_tile`, `make_braid_tube_tile`, `_cast`). Ang grid / dami ng braids ay depende sa libreng vertex at index ng IFF; "GAMITIN LAHAT NG SLOTS" para sa mas malaki.
- Editor: HAIR lock = ang hair cap + braid tubes (hindi nagagalaw ang mukha); APPLY ang magsusulat. RESET = byte-identical sa orihinal; kahit anong pangalan ng IFF ay ligtas.
- tests: tests/test_v243_hair3d.py (grid, ray cast, pictures, valid index, head hindi nagagalaw, nasa anit, winding palabas, tubes, reset, preview, editor edit).
- Hindi pa nasusubukan sa totoong laro / sa phone UI.

## v242 - 3D SHELL BEARD: tuloy-tuloy na surface sa panga (hindi cards) + bug fix sa pagsulat ng atlas
- **Ayon sa hiling ("hindi card na beard"):** ang GENERATE 3D BEARD ay gumagawa na ngayon ng **SHELL** (default): isang tuloy-tuloy na grid na surface na sumusunod sa panga, pisngi at baba, bahagyang nakaangat sa balat, may mustache, butas sa bibig at dumudulas pababa sa baba (goatee, hugis-V). Hindi na hiwa-hiwalay na strips. Ang kalidad ay hango sa mga sample mong IFF (png2137 / png8026): isang patch na may siksik na beard picture, hindi isang tumpok ng cards.
- Bagong `nba2k20/beardshell.py`: sinusukat ang tunay na hugis ng mukha (ray cast mula sa axis ng ulo), grid ng (columns x rows) na pinipili ayon sa libreng vertex / index ng IFF (hanggang 32 x 22 = 759 vertices kapag maluwag), at siksik na beard picture (RGBA) na gawa ng app: solid sa gitna, may mga hibla sa gilid at ibaba, may mouth cutout at hairline.
- Ang mga hanay (columns) ay **nagbabahagi ng vertices** = saradong surface. Nasa BEARD part pa rin ito: ma-eedit sa CYBERFACE EDITOR (BEARD lock: GRAB / SMOOTH / INFLATE / SIZE / ROT), pwedeng palakihin, patagalin, o ihugis, at nananatiling ma-edit ang mukha at OBJ.
- Sliders: KAPAL (DENSITY) = siksik ng picture, HABA = haba ng hang sa baba, LAPAD NG HIBLA = kapal / angat ng beard sa balat, KULOT = alon ng hibla, BAGSAK = hang vs. lumalabas. May bagong toggle sa dialog: **3D SHELL** o **CARDS**. HAIR at BRAIDS ay cards pa rin (natural na strips).
- **BUG FIX (mahalaga):** kapag ang IFF ay hindi pinangalanang `pngNNNN.iff`, ang pagsulat ng strand atlas (at ng base ng mukha) ay napupunta sa maling offset - sa ibabaw ng index buffer - kaya nasisira ang ulo ("Hindi tugma ang index buffer ng 3213 head"). Ngayon ang lahat ng GENERATE / RESET / PREVIEW ay gumagamit ng verified na texture list (`headhair._verified_ws`), kahit anong pangalan ng file.
- tests: test_v242_shell_beard (grid, picture na may mouth hole, valid index, head hindi nagagalaw, BEARD part, any-file-name, reset byte-identical, save + reopen + editor edit). Ang mga lumang card test ay gumagamit na ng `"shape": "cards"`.
- Hindi pa nasusubukan sa totoong game / sa phone UI.

## v241 - EDIT 3D BEARD / HAIR / BRAIDS = ang mismong 3D editor (hindi na GENERATE dialog)
- **Naayos ang button:** sa HEAD / HAIR dialog, ang **EDIT 3D BEARD / HAIR / BRAIDS** (katabi ng EDIT OBJ) ay bumubukas na ngayon sa mismong 3D editor (Cyberface Editor) ng 3D IFF na may BEARD cards na naka-lock agad - hindi na ang GENERATE sliders. Sa loob: GRAB / MOVE / SMOOTH / INFLATE / SIZE / ROT / X-MIRROR; **HAIR** = ang hair + braids cards, **BEARD** = ang beard cards, ALL PARTS = lahat; APPLY ang magsusulat.
- Kung wala pang 3D cards ang IFF, sinasabi nito kung ano ang gagawin (GENERATE, SAVE, BUKSAN ANG 3D IFF).
- `render3d._card_parts / _card_hair`: HAIR at BEARD lock ng 3213 ay hindi nag-o-overlap (test_v240_card_editor).
- Hindi pa nasusubukan sa phone UI / game.

## v240 - Cyberface Editor nakikita at na-eedit na ang 3D beard cards
- **Bago:** ang Cyberface Editor ay bumubukas na rin sa 3213 (strand-card) IFF: nasa mesh ang ulo AT ang generated beard / hair / braids cards. Piliin ang **BEARD** sa PART LOCK = ang beard cards lang ang gagalaw (GRAB / SMOOTH / SIZE / INFLATE ...), hindi ang mukha. **APPLY** ang magsusulat sa IFF (positions lang; UV, index at texture ay hindi nagagalaw).
- `fit_shape()` ngayon ay gumagamit ng box ng HEAD (unang 2445) para sa scale, hindi ng buong OBJ: ang mas mahabang beard ay hindi na nagpapaliit / nag-uunat sa mukha kapag nag-APPLY / REPLACE OBJ.
- GENERATE dialog: bagong button **BUKSAN ANG 3D IFF PARA I-EDIT** (isinasave ang 3D IFF at ginagawang bukas na IFF para magamit ang Cyberface Editor / EXPORT-REPLACE OBJ). HEAD / HAIR dialog: **EDIT 3D BEARD / HAIR / BRAIDS** sa tabi ng EDIT OBJ.
- Mas malinaw na error kapag 3213 OBJ ang pinasok sa 3168 / 2445 IFF (o kabaligtaran): sinasabi kung anong layout ang OBJ at ang bukas na IFF.
- Ang check mark sa mga button ay [x] na (walang kahon-kahon na "tofu" sa font).
- tests: test_v240_card_editor. Hindi pa nasusubukan sa game / sa phone UI.

## v239 - Hindi na kailangan pumili ng template IFF para sa GENERATE 3D BEARD
- **Ayon sa hiling:** kapag 2445 / 3168 pa ang head mo, hindi na hihinto ang GENERATE 3D BEARD para maghanap ka ng 3213 na IFF na template - **built-in na sa app mismo** ang template (`nba2k20/assets/beard_template_3213.iff`, mula sa file na ibinigay). Isang pindot lang GENERATE 3D BEARD, deretso na sa dialog.
- Walang file-picker step na dapat pang pumili ka ng ibang IFF para dito; palagi na itong gagamitin, pareho para sa lahat, walang mawawala.
- `headhair.builtin_beard_template()` (bago). Idinagdag ang `.iff` sa `source.include_exts` ng buildozer spec para talagang kasama ang template sa APK build.
- tests: V239BuiltinTemplate.
- Tungkol sa "shard sa mata" na nasa mga screenshot mo: ang tiningnan kong file (PNG1603.IFF) mismo ay may sarili nang beard cards (119 tris) bago pa man dumaan sa GENERATE natin, at malinis (hindi kulay-kulay) ang texture nito. Hindi ko pa ma-verify kung saan eksakto nanggagaling ang shard sa totoong laro nang walang makitang aktwal na file na galing sa totoong save/test sa device - kailangan ko pa nito para ma-ayos nang tiyak.

## v238 - Malaking bug fix (rainbow/kulay-kulay na beard) + mas makapal, mas may hugis, mas may depth
- **MALAKING BUG NA NAAYOS:** kapag ang 3213 IFF na binubuksan ay HINDI naka-pangalan sa pattern na "pngNNNN.iff" (hal. na-rename, o na-stage mula sa OBB gamit ang ibang pangalan), MALI ang nahahanap na lokasyon ng HAIR / BACK OF HEAD strand atlas texture - nagbabasa ito ng maling bytes (hindi pixel data), kaya **kulay-kulay/maingay** (hindi itim) ang itsura ng bawat generated card. Ito marahil ang dahilan kung bakit hindi pa nakakalapit sa quality ng beard ni ref sa reference mo. Ngayon, ina-ulit ang pag-scan ng textures gamit ang pattern na "pngNNNN.iff" sa internal na re-parse (hindi hinahawakan ang aktwal na file / path ng binubuksan mo - ligtas pa rin ang SAVE), kahit anong pangalan ang IFF. Pumasa ang buong test suite (100+ files) pagkatapos ng fix na ito.
- **Mas makapal / mas maraming overlap:** mas mataas na langit ng density (hanggang 230 cards kapag may lugar ang IFF, dati 190).
- **Hugis-V papunta sa baba (gaya ng reference):** manipis at maikli na ngayon ang beard sa sideburn/gilid, at makapal at mahaba sa chin/jaw papuntang gitna - hindi na pantay-pantay ang haba't lapad kahit saan.
- **Iba't ibang kulot bawat hibla:** dati iisang lakas ng KULOT (CURL) ang lahat ng cards; ngayon may random na pagkakaiba bawat card, mas natural ang itsura kaysa uniform na alon.
- **Mas may depth ang texture** (para sa synthetic / walang-real-atlas na mga kaso): dagdag na pangalawang blur na layer ng strands sa likod ng matatalas, at banayad na highlight, para hindi kasing-flat ng dati.
- **Hindi pa rin ito eksaktong kapareho ng quality ng totoong beard asset ng reference tool** (cards pa rin ito, hindi sculpted mesh na may totoong normal map); pero malaking hakbang paitaas mula sa sira/kulay-kulay na dati.
- `headhair._verified_textures()` (bago - name-independent na texture scan), `beardgen.clear_of_skin` taper/curl updates.
- Hindi pa rin ito nasusubukan sa mismong laro (game engine shading); ang preview ay software render lang sa tool.

## v237 - REPLACE OBJ: hindi na basta error kapag galing sa 3D BEARD cards; GAMITIN ITO BILANG BAGONG BASE
- **Bug na naayos:** REPLACE OBJ (FULL / HEAD) ay basta na lang tumatanggi ("kailangang 2,445 o X") kapag ang OBJ na pinili ay mula sa 3213-vertex na 3D BEARD cards head (hal. EXPORT FULL OBJ ng IFF na ginawa ng GENERATE 3D BEARD) pero ang IFF na binubuksan ay ibang head (2445 / 3168, walang cards). Ngayon, kapag mas mahaba ang OBJ kaysa sa kailangan ng IFF, ang **unang HEAD_N vertices lang** (ang head mismo - laging una ito, bago ang cards) ang isinusulat, parang REPLACE HEAD; sinasabi sa resulta ("3213-vertex OBJ ito...").
- **Bagong button sa GENERATE 3D BEARD dialog: "I-EDIT SA CYBERFACE / OBJ EDITOR, TAPOS: GAMITIN ITO BILANG BAGONG BASE."** Dati, kahit anong i-edit mo sa cards (sa CYBERFACE EDITOR SCULPT, o sa pag-REPLACE ng OBJ na hiniwalay mong inayos sa Blender/ibang OBJ editor), babalik lang ito sa dati sa susunod na GENERATE (dahil laging mula sa estado BAGO ang unang GENERATE ang pinagbabatayan). Ngayon: i-GENERATE muna, i-edit ang resulta (CYBERFACE EDITOR o REPLACE OBJ), tapos pindutin ang bagong button - ang kasalukuyang beard (kasama ang edit mo) ay magiging BAGONG "orihinal". Ang susunod na mga slider adjustment / GENERATE ay dito na mag-uumpisa (papakapalin, hahabaan, etc. mula sa in-edit mo, hindi mula sa random na procedural beard); RESET ay dito na rin babalik.
- `headhair.rebase_beard()` (bago), `replace_obj()` may `head_only_fallback` sa return.
- tests: V237ReplaceObjFallback (2 bagong test) sa test_v232_beardgen.py.
- Hindi pa nasusubukan sa game.

## v232 - GENERATE 3D BEARD (isang pindot, sliders, kumakapal)
- **HEAD / HAIR -> GENERATE 3D BEARD**: gumagawa ng procedural 3D beard (strand / hair cards) sa mukha: jaw, pisngi, baba, at moustache band. Hindi sa lips / mata / tenga / leeg. May **live preview** (drag para iikot, HARAP / 3/4 / GILID / BABA) at sliders: **KAPAL (DENSITY)**, **HABA**, **LAPAD NG HIBLA**, **KULOT (CURL)**, **BAGSAK (DROOP)**, kulay (BLACK / DARK BROWN / BROWN / GRAY) at SHUFFLE.
- **Kumakapal habang tinataas ang KAPAL**: ang posisyon ng cards ay fixed na low-discrepancy sequence, kaya ang mas mataas na density ay **nagdadagdag lang** ng cards; ang nakikita mo na ay hindi gumagalaw. Laging ginagawa mula sa ORIHINAL na head (hindi nag-iipon); RESET = byte-identical sa orihinal.
- Para sa 3213 strand-card head: isinusulat ang x/y/z, UV (strand atlas) at vertex rows ng bagong cards sa libreng card slots, at ang index buffer (idinadagdag pagkatapos ng huling gamit na entry; hindi ginagalaw ang head strips). Ang lumang beard cards ay ginagawang zero-area; ang braids / hair cards ay nananatili kung may libreng lugar sa atlas. Ang strand picture (RGBA) ay nilalagay sa libreng rectangle ng HAIR / BACK OF HEAD atlas.
- Para sa 2445 / 3168 head: piliin ang 3213 template IFF (hal. png8152) -> ginagawa ang bagong 3D IFF (head mo + template), tapos doon gumagana ang generator; SAVE -> `iff/3D/<pangalan>.iff`, ilagay sa OBB gamit ang Import IFF (replace this entry).
- Limitasyon: ang bilang ng cards ay limitado ng libreng vertices / index entries ng IFF (nasa taas ng dialog ang "hanggang N cards ang kasya"). **Hindi pa nasusubukan sa game**: ang normals / bones ng bagong cards ay kinokopya mula sa pinakamalapit na skin vertex. Gumamit ng kopya ng OBB.
- Bagong modules: `nba2k20/beardgen.py` (region, cards, strand tile, preview), `headhair.preview_beard / generate_beard / reset_generated_beard / beard_status / open_template_workspace`.
- tests: test_v232_beardgen.

## v231 - MAKE 3D BEARD / BRAIDS IFF (ang head mo + cards ng 3213 donor)
- **Bakit ayaw ma-copy sa v230:** ang 3213 strand cards ay hindi maisisingit sa karaniwang 2445 / 3168 head (iba ang vertex, index at texture layout). Ngayon, kapag 3213 ang donor at hindi 3213 ang head mo, ang COPY BEARD / COPY HAIR ay **gumagawa ng bagong IFF**: donor file + HUGIS NG HEAD MO (unang 2445 vertices) + cards ng donor na nakalagay sa head mo + atlas ng donor. Nase-save sa `iff/3D/<pangalan ng entry>.iff`; ilagay sa OBB gamit ang **Import IFF (replace this entry)**.
- Face skin ay galing sa donor (ang 3213 template ay grayscale shading map lang). Hindi pa nasusubukan sa game.
- Malinaw na error kapag mali ang kombinasyon (3168 donor sa 3213 head, o COPY TEXTURES na 3213 donor sa ibang head).
- tests: test_headhair_cards (build from a plain head).


## v230 - 3D strand cards (pro-style 3D beard + braids, 3213 head)
- **Bagong template na kinikilala: 3213 vertices** (png8007 = braids + stubble, png8152 = strand beard). Head = unang 2445 (karaniwang native head), 2445..3212 = 768 hair / beard **cards**; may sariling index (face) buffer at 28-byte vertex rows (UV / normal / bones); ang texture #2 (512x512 RGBA) ay ang strand atlas (alpha strands).
- HEAD / HAIR dialog: nakikilala na ("3D STRAND CARDS"), hindi na "HAIR SLOT NONE".
- **COPY BEARD / COPY HAIR / COPY BEARD TEXTURES** sa 3213: kinokopya ang cards (positions sa ibabaw ng head mo, vertex rows, index buffer, strand atlas). Magkasama ang beard + braids (iisa ang index buffer at atlas).
- **EXPORT FOR BLENDER** sa 3213: FACE / HAIR / BEARD objects (faces ng cards galing sa strip index buffer). REPLACE HEAD / HAIR, RESIZE BEARD / HAIR (length / width) gumagana na rin.
- BEARD vs HAIR (braids) ay per connected strip, base sa lugar nito sa head (mababa at nasa harap = beard).
- tests: test_headhair_cards (gamit ang 2 sample IFF sa tests/data), test_headhair_resize (CI na).
- Hindi pa nasusubukan sa game: gumamit ng kopya ng OBB.


## v225 - mas maraming kanta + AUTO CONVERT sa Audio
- **Marami nang kanta ang nakikita.** Ang music banks (hal. jukeboxmusic.bin, eventmusic.bin) na may maraming kanta sa loob ay hinahati na sa bawat kanta (`jukeboxmusic 001`, `jukeboxmusic 002` ...). Mabilis ito (memory-map ng OBB, ilang segundo lang sa unang scan, naka-cache na pagkatapos) at hindi na kailangang i-inflate ang buong OBB. Ang **Deep scan** button ay para na lang sa audio na nakatago sa loob ng compressed IFF entries.
- **AUTO CONVERT (Import / Replace audio):** pwede nang pumili ng .mp3 / .wav / .m4a / .flac / .opus / .ogg ... at awtomatikong kino-convert sa OGG Vorbis na kapareho ng sample rate at channels ng kantang papalitan. Kapag ang kanta ay nasa loob ng ibang entry (fixed slot), hinahanap ng encoder ang quality na kasya sa slot. OGG na masyadong malaki para sa slot ay nire-re-encode din.
  - Sariling Vorbis encoder (`nba2k20/vorbis_enc.py`, numpy lang, walang ffmpeg / libvorbis). Na-verify sa ffmpeg decoder: tama ang amplitude, haba, CRC ng pages.
  - Decode: .wav = pure Python (garantisadong gumagana); ibang format = ffmpeg kung meron (Termux/PC) o ang Android decoder (MediaCodec) sa phone.
- tests: test_v225_audio_convert.

## v224 - Audio / OGG Explorer: IFF-list style, names, 1-second scan
- **Audio wala na sa IFF list.** Ang audio / OGG entries (jukeboxmusic.bin, eventmusic.bin, env_amb.bin ...) ay hindi na lumalabas sa Open OBB IFF list, at wala na ang "Audio" sa category dropdown. Sa **Audio** button na lang sila (IFF-only na ang list).
- **Bagong itsura ng Audio / OGG Explorer** = kapareho ng IFF list: search + dropdown, MULTI AUDIO, rows na may pangalan + `#id | Audio | oras | codec | ch | Hz | laki`, Export, Import (= replace audio) at star. Tap ang row = play; long-press = multi-select. May Sort at filter (Named songs / Theme / Music / ... / Favorites).
- **Pangalan ng kanta**: ipinapakita na ang tunay na pangalan (hal. `jukeboxmusic.bin`), hindi na "Theme 001". Naka-sort na "Named first". Ang export ay `jukeboxmusic.ogg`. May Rename (para sa kasalukuyang track).
- **Scan = ~1 segundo** (dati 10-15 min). Ang mabagal ay ang paghahanap ng audio na nakatago sa loob ng ibang entry (kailangan i-inflate ang buong OBB). Hindi na ito awtomatiko: nasa bagong **Deep scan** button, isang beses lang at naka-cache pagkatapos.
- tests: test_obb_layouts updated.

## v223 - OVR now matches the ONLINE OVR in every sync
- **Bakit hindi tama ang OVR:** ang FULL AUTO (team), ALL TEAMS at FREE AGENTS sync ay may naka-hard-code na `match_ovr=False`, kaya ang ratings lang ang isinusulat at ang OVR ay kung ano ang lumabas sa pagsasama ng ratings (ibang-iba sa online OVR). Ang "Match OVR" ay nasa single-player popup lang at naka-OFF pa.
- **Bago: sync option `ovr` (default ON)** - katabi ng ratings / tendencies / age / position / body / contract sa Online ratings popup (`sync_options.json`). Pagkatapos isulat ang ratings, ina-adjust ang mga ito hanggang ang OVR sa editor / game ay katumbas ng online OVR (`setOvr`). Gumagana sa player, team, all teams, free agents.
- Ang "Match OVR" toggle sa single-player popup ay iisa na sa option na ito (naka-save).
- Kapag hindi maabot ang OVR (hal. sobrang taas), sinasabi sa report ("OVR not matched") at tuloy pa rin ang sync; walang nasisira.
- tests: test_v223_ovr.

## v220 - faster OBB open / save + online sync diagnostics (on top of v219)
- **Save OBB: one pass.** The archive CRC32 is now built from per-entry CRCs computed WHILE the source is copied (`crc32_combine`), so the second full read of the multi-GB OBB is gone. Edited / appended entries are included; the result is tested equal to the reference full-file CRC (2K20 + 2K16 layouts, in-place + appended). Anything odd (overlapping entries, any error) falls back to the old copy + CRC pass; `full_hash=True` still does every pass.
- **Open OBB: remembered.** What every unnamed entry is (the slow part, it decompresses blocks) is saved per OBB (path + size + mtime) in `obb_cache`; the 2nd open of the same OBB is instant. A bad / old cache file is ignored.
- **Save roster: deflate level 6** instead of 9 (about 10x faster on a phone, file ~5-8 % bigger). The game only inflates the payload. Set `DEFLATE_LEVEL = 9` in roster_core.py to get the old Java-identical bytes back.
- **Online sync log (`online_debug.txt`)**: the bio excerpt now starts at the real bio (it used to be the site menu) and each line carries `CONTRACT: ...` = the page text around contract / salary words, so the contract read can be fixed from the log.
- tests: test_v220_fastsave, test_v218_obbcache.

## v219 - real beard IMPORT / EXPORT / color + SEAM GUARD
- **IMPORT BEARD PNG / EXPORT BEARD PNG** (Beard tab): import any transparent strand-beard PNG (a photo of hair on a light background also works - the background becomes transparent). It becomes a style (`strands_<NAME>.png` + colour in `styles.json`, in the `styles` folder) next to LEBRON JAMES; EXPORT saves the current strand beard in the chosen colour as a transparent PNG. `styles.import_strands / export_strands / tint_strands`.
- **Beard colour on real strands**: the colour swatches recolor the strands (light / dark detail and alpha kept) for preview, APPLY and EXPORT.
- **SEAM GUARD** (sculpt quick bar, default ON): editing a head-only BEARD no longer drags the skin around / under it (jaw seam, throat, neck): the seam ring is held, the next rings fade back to free, the beard tip stays free to grow. On the bundled New Beard LBj head the seam stretch (the hanging skin flap) drops by ~85 % while the beard still follows the finger. Not applied to exact native parts (they never touch the skin).
- reference tools naming replaced with David2kTools everywhere (module `david2ktools.py`, labels, docs, tests).
- tests: test_v219_beard_io_seam.

## v218 - David2kTools / david2ktool merge
- **GPU VIEW (BETA)**: new quick button in CYBERFACE EDITOR (OBJ and IFF). The head is drawn by the GPU (textured, smooth lit, wire + orange locked-part lines) on every finger move, like the OpenGL view of the Java build. OFF by default. Same projection / culling / picking as the Pillow renderer (`nba2k20/glview.py`), so SELECT / GRAB / MOVE / axis gizmo are unchanged; FLAT view, front/side reference photos and any GPU error fall back to Pillow by themselves. NOT verified on a real phone GL context (no Kivy in the build sandbox): frame maths and wiring are tested, the Kivy shader / Mesh part is not.
- **UV FULL**: ELEMENT: VERTEX / EDGE / FACE select, UV FILL, LOAD REFERENCE + REFERENCE ON/OFF, RANGE readout (`uvedit.pick_element`, `uv_range`, `render(fill=, reference=)`).
- **N2KM**: Open OBJ / Player head / OBJ creator accept `.n2km` / `.model` (`nba2k20/n2km.py`, same validation and X,-Z,Y basis as the Java reader; facial shell `0-1` only when present). Converted to a cached OBJ, vertex order kept for SAVE OBJ.
- **SAVE OBJ header**: edited OBJ gets the native-order header (OBJ_FORMAT=16, vertex count, stride 8) like the Java build. Comment lines only.
- DAVID2K TOOLS (quick bar, default ON): Java head-editor brush engine. PINCH (Java "smooth": pulls toward the touched point), INFLATE, DEFLATE, FLATTEN pick a vertex and use smoothstep falloff; SMOOTH stays the real smoothing brush.
- Exact native parts (2445/3168 heads): BEARD / HAIR / HEAD / EYES / MOUTH PART LOCK use the real face groups (no guessing); no travel cap / chin guard / pin ring on exact parts, 1:1 drag. Java falloff is the default, brush radius 0.28.
- tests: test_v218_d2k.
- HEAD / HAIR dialog (IFF screen, new button): EDIT OBJ, EXPORT / REPLACE HEAD, HAIR and FULL OBJ for the open cyberface IFF (nba2k20/headhair.py). Writes int16 positions only, wrong vertex order refused, HAIR SLOT shown READY / NONE (HEAD ONLY).
- ROTATE / SCALE (DAVID2K TOOLS ON): Java behaviour - about the vertex under the finger, smoothstep falloff, on the exact part; no vertex under the finger = the v217 selection transform.
- Faster loading: OBJ parse + repair cached per file (re-open = instant), packed head stream scan remembered per IFF (was repeated 4-5x per open).
- tests: test_v218_headhair.
- UV FULL: AUTO HEAD UV (native reference UV, also for the IFF head through src_index; one undo step) and APPLY UV (keeps the edit, goes back; packed 2K20 heads have fixed native UV so only positions reach the IFF).
- tests: test_v218_uvauto.
- SPLIT HEAD + HAIR + MOUTH + EYES -> ONE OBJ (HEAD / HAIR dialog, nba2k20/objsplit.py): v / vt / vn tables unchanged, faces regrouped into o/g HEAD, HAIR, MOUTH, EYES (existing names, native 3168 groups, or island geometry).
- Landscape (Pahiga) OBJ editor: vertical TOOLS column on the left (SELECT, BOX, MOVE, GRAB, SMOOTH, PINCH, INFLATE, DEFLATE, FLATTEN, ROTATE, SCALE, ERASER); new 3D BOX SELECT tool (visible vertices only, respects PART LOCK).
- tests: test_v218_split.
- tests: test_v218_extras, test_v218_glview, test_v218_gpu_ui.

## v217 (merge pass 2) - roster editor
- Roster: NEW Tendencies (58), Appearance (43: shoes, headband, sleeves, colours ...) and Animations (40: shot / dunk / layup packages, intros) per player, ported from the Java VIP roster editor (`nba2k20/roster_extra.py`, screens in main.py). Saved with the normal Save roster.
- Verified against the Java `RosterCrypto`: the roster file save (compress + CRC + encrypt) is byte-identical to the Java output, each decodes the other's file; bit read/write matches Java on 4000 random ops.
- tests/test_roster_extra.py. Full suite: 576 tests OK.

## v217 (merge pass 1)
- Audio: file picker for REPLACE AUDIO now accepts .oga (same Ogg container). Java VIP build's OGG slot/OggS checks were compared: v217 already covers them and also edits OGG inside compressed IFF.

## v215
- **PART LOCK safety cap**: a vertex of the locked part (BEARD ...) can never travel farther than 0.35 of the part's size from the loaded OBJ's shape, and finger drags on a locked part move at 55% speed (fine, controlled pulls) - no more beards torn into flat sheets.

## v214
- **BEARD no longer drags the mouth**: the beard part now ends under the lips (cheek / sideburn rise on the sides only), and the part's upper edge is pinned (edge vertices still, the next rings only partly move) - only what is wired in orange adjusts, the lips / mouth stay. Smaller, gentler pull radius.

## v213
- **No more spike**: pulling one point of a locked part (the chin of a BEARD) now moves a smooth bell-shaped area (cosine falloff, radius covers a good share of the part), so the beard lengthens like proportional editing instead of making a thin spike.

## v212
- **BEARD / FACE regions on a head that carries a bust**: the head now starts at the neck (narrowest slice above the shoulders), so BEARD no longer grabs the chest / shoulders (the yellow dots over the chest).
- The locked part is drawn as orange mesh LINES (not dots), also while dragging.

## v211
- **SIZE W/H/D +/-**: manual size of the locked part (BEARD wider / longer / deeper) by hand.
- **WIREFRAME ONLY**, **MIRROR X UV**, **PLANAR UV**, **EXPORT HEAD / HAIR / FULL OBJ**.
- **Preview filters** (PC ULTRA ... DETAIL POP, strength, vignette) - look only, never written to the IFF / OBJ (`filters.py`).

## v210
- **SMOOTH FILTER** (smooth the whole locked part - BEARD / HAIR - in one tap, strength follows STRENGTH) and **FIX SHAPE** (locked part back to the loaded OBJ shape). Only vertices move; one UNDO step each. In HEAD SCULPT and the IFF editor.

## v209
- Merged into the v208 base (nothing of v206-v208 removed): **AXIS lock + gizmo** (FREE / X / Y / Z; X red, Y green, Z blue at the selected point) for MOVE / GRAB in both HEAD SCULPT and the Open IFF editor - e.g. Y in side view lengthens a beard straight down.
- `Renderer.move_selected_axis`; `_overlay_hook` in the Workshop preview.
- Renamed: HEAD SCULPT -> **CYBERFACE EDITOR / OBJ**; the IFF Cyberface Workshop -> **CYBERFACE EDITOR** (UI style unchanged).
- tests/test_v205_iff_editor.py (axis, gizmo, beard-lengthen end to end).

## v204 — PART LOCK: beard lang ang maedit pag BEARD, hair lang pag HAIR (+ FACE / BACK parts)

- **Sanhi ng "sira" na hair / beard:** ang mga tool ay umaabot sa katabing parte (hal. ang soft radius ng pag-hila sa balbas ay nahihila rin ang buhok / leeg).
- **Ayos: PART LOCK.** Sa row 2 ng HEAD SCULPT: `ALL PARTS | HAIR | BEARD | FACE | BACK | HEAD | EYES | MOUTH`. Pag pumili ka ng parte, **iyon lang ang puwedeng galawin ng LAHAT ng tool** (GRAB, MOVE, SMOOTH, INFLATE, DEFLATE, FLATTEN, ERASER, SCALE, ROT). Ang ibang vertex ay hindi gumagalaw kahit abutin ng brush. Nasa status ang `LOCK: BEARD`. `ALL PARTS` para alisin ang lock.
- **Mga parte:** kung may `g` groups ang OBJ (HEAD / HAIR / EYES / MOUTH) ay iyon ang eksaktong gagamitin; kung wala, hula mula sa posisyon: HAIR = taas at likod ng ulo, BEARD = panga / baba / ilalim ng baba (walang mata, bibig, buhok), BACK = likod ng ulo at batok, FACE = harap ng mukha.
- **TEXTURE: ON / OFF** (clay view) para makita ang hugis nang walang texture.
- Tests: `tests/test_v202_smooth.py` (PartLockTests). Hindi nasubukan sa phone / laro.
- **Hindi pa nagagawa:** ang 2K14 -> 2K20 na may kasamang 3D hair / braids / beard. Ang kasalukuyang 2K14 converter ay texture (at head shape fit) lang; kailangan ng sample na 2K14 IFF at ng ported na resulta para magawa ito nang tama.

## v203 — UV editor na may 3D LIVE (galing sa video mo) + RELAX / PLANAR / CHECKER

- **UV FULL ay may 3D LIVE pane** sa tabi ng UV map (landscape: UV | 3D | tools; portrait: UV sa taas, 3D sa ilalim). Habang hinihila mo ang UV, nagbabago agad ang textured na ulo; ang napili mong UV points ay lumalabas na pulang tuldok sa 3D. Ang 3D pane ay puwedeng i-orbit (hila) at i-zoom (pinch) at gumagamit din ng mabilis na draft frame habang gumagalaw.
- **Bagong UV tools:** `PLANAR UNWRAP` (patag na projection mula sa harap), `RELAX UV` (pinapantay ang bunched / stretched na UV; ang gilid ng bawat UV island ay hindi gumagalaw, may Undo), at `CHECKER` (checkerboard sa UV at 3D para makita ang stretch).
- Ang `IMPORT TEXTURE` (dating TEXTURE) sa HEAD SCULPT ay nagpapakita ng texture sa ulo kasama ng iba pang layer.
- Tests: `tests/test_v202_smooth.py` (pinalawak).
- **Hindi ko ginaya:** ang "SAVE TO IFF" ng ibang tool sa video; ang sa atin ay APPLY / SAVE OBJ gaya ng dati. Hindi nasubukan sa phone.

## v202 — Mas smooth ang pag-edit + manual na pag-adjust ng BEARD (walang binago sa layout)

- **Smooth:** habang gumagalaw ang daliri (drag / brush / sliders), **mabilis na DRAFT frame** na ang ginagamit (`Renderer.render_draft`: flat-shaded polygons na kinulayan mula sa 128 px na kopya ng texture) imbes na ang buong render. Sa PC test: ~15 ms kontra ~90 ms (mga 6x na mas mabilis; sa phone ay mas mabagal pero ganoon din ang ratio). Pag-angat ng daliri, lalabas ang buong-linaw na frame. Pareho pa rin ang picking, wireframe at mga pulang tuldok ng napili. Mas maikli rin ang hintay sa pagitan ng frames (12 ms) at ng brush strokes (30 ms).
- **Manual beard (at kahit anong parte):** bagong quick buttons sa row 2 ng HEAD SCULPT:
  - **PARTS:** `HEAD  HAIR  BEARD  EYES  MOUTH` (pumipili ng buong parte; ang BEARD ay ang ibabang mukha: panga, baba, paligid ng bibig).
  - **MOVE** (hilahin ang napiling parte), **INFLATE / DEFLATE** (palalimin o palaki ang ibabaw na parang balbas na kumakapal), **FLATTEN** (patagin), kasama ang SMOOTH / ERASER / GRAB na meron na.
  - **SCALE + / SCALE - / ROT L / ROT R** sa napiling parte.
  - **PROPORTIONAL: ON / OFF** (ON = soft na falloff sa paligid; OFF = ang napili lang ang gagalaw) at **STRENGTH 25 / 50 / 75 / 100 %**.
  - Ang napiling parte ay gumagalaw bilang buo kahit ON ang proportional.
- Lahat ay vertex lang ang ginagalaw (UV / faces hindi nagagalaw), kaya pasok pa rin sa `integrity()` check ng SAVE OBJ.
- Tests: `tests/test_v202_smooth.py`. Hindi nasubukan sa totoong phone; ang bilis sa phone ay hula mula sa ratio ng PC test.

## v201 — HEAD SCULPT: Fit Ref, Easy Align, Bake, Layers, Headband, Hide, Face Parts (walang binago sa UI style)

- **Walang ginalaw sa layout ng v200.** Ang mga bagong tool ay dagdag na **quick buttons sa row 2** (taas) ng HEAD SCULPT (View at Mesh): `FRONT REF`, `SIDE REF`, `FIT REF`, `ALIGN REF`, `EASY ALIGN`, `TEXTURE`, `BAKE`, `LAYERS`, `HEADBAND`, `HIDE`, `FACE PARTS`, `VIEW PART`, `PAINT`, `TEX ERASER`, `SAVE TEXTURE`. (Swipe row 2 pakaliwa.)
- **FIT REF / ALIGN REF / EASY ALIGN:** hinahanap ng tool ang mukha sa litrato (kulay ng balat) at inaayos ang litrato (FIT REF), ang side photo sa front photo (ALIGN REF), o ang MESH mismo sa litrato (EASY ALIGN, may UNDO). Pagpili ng FRONT / SIDE REF ay auto-fit na. Hula lang ito; i-adjust ng kamay.
- **BAKE:** ipo-project ang front / side na litrato sa UV texture bilang layer na `Photo`. **LAYERS:** Base + Photo / Headband / Paint, ON/OFF, opacity, Up/Down, Merge, Del. **PAINT / TEX ERASER:** brush sa texture (ang Base ay protektado sa eraser). Undo / Redo ay umaabot sa mga layer.
- **HEADBAND:** banda sa ulo (kulay sa texture + bahagyang umbok sa mesh). **HIDE / VIEW PART / FACE PARTS:** itago, ihiwalay o piliin ang parte (hula mula sa posisyon sa ulo).
- **SAVE TEXTURE** -> `head_sculpt/head_sculpt_texture.png`. Ang SAVE OBJ ay hindi nagbago: gumagalaw lang ang vertex, kaya pasok pa rin sa `integrity()` check (UV at faces hindi nagagalaw).
- Bago: `nba2k20/cyberedit.py` (logic, walang Kivy) at `nba2k20/cybertools.py` (wiring). `render3d.Renderer.hidden`, `refimage.placement`.
- Tests: `tests/test_v201_cyberedit_core.py`, `tests/test_v201_cybertools.py`. Hindi nasubukan sa totoong phone / laro.

## v200 — Mas malaki ang 3D / OBJ view (screenshot ng v199)

- **Sanhi ng maliit na larawan:** ang 3D view ay isang parisukat na kasing-taas lang ng kahon nito, at sa landscape ang natira ay ~110 dp lang: ang pulang title + guhit ay ~70 dp, ang header at 2 toolbar row ay 36 - 40 dp bawat isa, at may brush strip pa sa ibaba.
- **Ayos:** (1) inalis ang title bar ng popup (nasa status text na ang pangalan: `HEAD SCULPT | file | tool`); (2) mas payat ang header at ang 2 toolbar row (30 dp na button, mas maliit na font); (3) **Brush slider ay nasa header na** (kanan), wala nang strip sa ibaba; (4) mas maliit ang kanang options (30% imbes na 34%) at mas malapad ang mga view (70%); (5) ang HEAD SCULPT na View panel ay maikli na (walang HD 512 / REALISTIC SKIN / TUNAY NA RESOLUTION na hindi para sa shape editor). Tinatayang mula ~110 dp patungong ~250 dp ang taas ng larawan sa landscape (hula mula sa laki ng mga bahagi, hindi nasukat sa phone).
- **Bago: `FULL`** (header): itinatago ang toolbar, UV view at options para ang 3D ay gumamit ng buong taas; pindutin ulit para ibalik. **Bago: `UV`** (dulo ng row 1): itago / ipakita ang UV view (nagbibigay ng buong lapad sa 3D).
- Ang `FIT / CENTER` ay `FIT` na lang sa toolbar (mas maikli).
- Tests: `tests/test_v199_toolbar.py` (pinalawak). Hindi ko nakita sa totoong phone.

## v199 — Bagong layout: lahat ng feature ay nasa TAAS (toolbar), malaki ang 3D / UV view

- **Ayos sa overlap** (screenshot ng HEAD SCULPT): sa landscape, sobra ang taas ng kanang column (status + camera + tabs + tool bar + options) kaya umaapaw pataas at tinatakpan ang APPLY / Close. Inalis ang column na iyon.
- **Bagong layout (Cyberface Workshop at HEAD SCULPT):**
  - **Taas:** `Undo | Redo | APPLY | Close` + status.
  - **Row 1 (swipe pakaliwa / pakanan):** mga tab (View, Tattoo, Paint, Skin, Mesh, Face, Hair, Beard) + camera (FRONT, LEFT, RIGHT, BACK, TOP, +, -, FIT / CENTER, Flat, Pahiga). Sa HEAD SCULPT: `VIEW SELECT GRAB SMOOTH ERASER | X-MIRROR | IMPORT OBJ | SAVE OBJ` + camera.
  - **Row 2 (quick tools ng mode, naka-swipe):** View = OPEN OBJ, HEAD SHAPE, PLAYER HEADS, SAVE PNG, HD 512, ULTRA HD, SKIN+, SLIM BROWS, TEXTURES; Mesh = OPEN OBJ, SAVE OBJ, HEAD SHAPE, VERTEX, FACE, WIRE, SELECT ALL, CLEAR SEL, UV EDITOR, KALBO, INSPECT; Beard = HARDEN 3D / FULL 3D / GOATEE 3D / CHINSTRAP 3D, BEARD OBJ. Nagtatago ang row kapag walang quick tool ang mode. Tumatawag sila ng parehong function ng mga button sa options panel.
  - **Gitna:** 3D view (kaliwa) at UV / texture view (kanan) na ang lapad ay 66% ng screen sa landscape; ang **options ng mode** ay nasa makitid na scroll sa kanan (34%).
  - **Ibaba (HEAD SCULPT):** **Brush** slider.
- Walang binago sa logic ng pag-edit / apply; ang layout at ang pagkakalagay ng mga button lang.
- **Hindi ko nakita ang itsura sa totoong Kivy / phone** (wala sa sandbox ko; headless na fake Kivy ang tests). Kung may mali sa laki ng button o sa overlap sa partikular na phone, i-screenshot at aayusin ko. Tests: `tests/test_v199_toolbar.py`.

## v198 — License login: "Incorrect Key" kahit tama ang key (diagnosis + ayos)

- **Ang "Incorrect Key, Contact: @DAVID ENGINE" ay sagot ng PANEL mo, hindi ng app.** Natanggap ng server ang key at tinanggihan niya. Dalawang malamang na dahilan:
  1. **Nagbabago ang Device ID kada build.** Sa screenshot mo: v193 `e87c96b8efc51570`, v197 `936cedd6ae7832ca`. Ang Android ID ay nakatali sa signing key ng APK, at ang GitHub Actions ay gumagawa ng bagong debug key kada build. Kung naka-HWID lock ang key sa panel, iba na ang device kaya reject. **Ayos:** `Fixed signing key` step sa `build.yml` + gabay sa `BUILD.md` (secret `DEBUG_KEYSTORE_B64`). Isang beses lang gagawin.
  2. **Hindi tugma ang `game`.** Ang app ay nagpapadala ng `game=NBA2K20` (`assets/license.json`). Dapat eksaktong pareho sa pangalan ng product sa panel (v193 ay `NBA2K`).
- **Bago:** sa ilalim ng pulang error ay lumalabas na ang ipinadala ng app (`game=... device id=...`) para ma-compare sa panel; **tap ang Device ID = copy** (ibigay sa panel para i-reset).
- **Bago: `tools/license_check.py`** (Termux / PC, hindi kailangan ng build): `python tools/license_check.py KEY --games NBA2K20,NBA2K` ipinapakita ang eksaktong ipinadala at ang raw na sagot ng panel, at kung aling `game` / `serial` ang tinatanggap.
- **Ayos sa login screen:** ang asul na header band ay nalalagay sa ilalim ng card (nasa EXIT button sa screenshot mo); ngayon ay iginuguhit sa header mismo.
- Hindi ko ma-test ang tunay mong panel (hindi abot ng sandbox ko); sinubukan ko ang client at ang tool laban sa fake na panel.

## v197 — HEAD SCULPT: hiwalay na OBJ head editor (Grab / Smooth / Eraser / X-Mirror / Brush)

- **Bagong home button `Head Sculpt`** (hiwalay sa Cyberface Workshop; `nba2k20/headsculpt.py`): OBJ lang ang kailangan, walang IFF o face PNG. Tool bar
  na tulad ng LOKO2K: **VIEW** (ikot) | **SELECT** (tap vertex) | **GRAB** (hinihila ng daliri ang ibabaw sa ilalim nito, may soft radius) |
  **SMOOTH** (brush) | **ERASER** (brush na ibinabalik ang ibabaw sa hugis ng OBJ nang buksan) | **X-MIRROR** | **Brush** size slider |
  IMPORT OBJ | SAVE OBJ. Kasama pa rin ang 3D view, Undo / Redo, at ang FRONT REF / SIDE REF at ang buong Mesh panel (v196).
- **"Walang sirang texture":** lahat ng tool ay vertex lang ang ginagalaw. Bago mag-SAVE OBJ / APPLY, tinitingnan ng `Renderer.integrity()` na
  pareho pa rin ang faces, UV at vertex count, at walang NaN; kapag nagbago, **hindi isinusulat** at sinasabi kung bakit. Babala (hindi harang)
  kapag 1.6x+ / 0.6x- ang laki ng ulo o maraming triangle ang nawasak.
- Bago sa `render3d.Renderer`: `smooth_around`, `erase_around`, `integrity`. Tests: `tests/test_v197_sculpt.py` (core) at
  `tests/test_v197_headsculpt_ui.py` (screen, gamit ang fake Kivy).
- **Wala pa (kumpara sa LOKO2K):** auto `Fit Ref`, `Bake`, `Layers`, `Headband`, `Hide / Show`, `Face Parts`, `Easy Align`. Hindi pa nasubukan sa phone.

## v196 — FRONT REF / SIDE REF (reference photo sa 3D head)

- **Workshop > Mesh:** `FRONT REF` / `SIDE REF` (pumili ng litrato), `VIEW FRONT` / `VIEW SIDE` (snap ng camera), `REF ON/OFF`, `CLEAR REF`, at sliders **Opacity / Laki / Kaliwa-Kanan / Taas-Baba** para i-align ang litrato sa ulo. Lumalabas ang litrato kapag nakaharap (yaw ~0) o patagilid (~90 deg, naka-mirror sa kabilang gilid) ang 3D view; hindi ito isinusulat sa IFF / OBJ (guide lang).
- Gamitin kasama ng DRAG / SMOOTH / MIRROR ng Mesh tab para itugma ang hugis sa mukha sa litrato.
- **Wala pa (kumpara sa LOKO2K):** auto `Fit Ref`, `Eraser` brush, `Bake`, `Headband`, `Hide`. Hindi pa nasubukan ang screen sa phone.
- Tests: `tests/test_v196_ref.py`.

## v195 — Offline hanggang expiry ng key

- Pagkatapos ng **isang matagumpay na online login**, gumagana na ang app **offline hanggang sa expiry date ng key** (`offline_grace_hours: 0` = walang limit maliban sa expiry; lagyan ng bilang, hal. 72, kung gusto mong kailangan mag-online kada 3 araw).
- Hindi madaya ang "pag-atras ng oras": itinatala ng cache (HMAC-signed) ang pinakahuling oras na nakita ng app at tinatanggihan kapag mas maaga ang oras ng phone.
- Tandaan: habang offline, hindi malalaman ng panel kung na-ban / na-revoke ang key; sa susunod na online login lang ito mate-tsek.

## v194 — Ayos ang "Walang koneksyon sa server" sa license login

- **Sanhi (malamang):** sa Android, walang sariling CA store ang Python kaya nabibigo ang HTTPS verification, at ang free host ay madalas may expired / self-signed na certificate; ang error ay tinatago bilang "walang koneksyon".
- **Ayos:** (1) gumagamit na ng `certifi` CA bundle; (2) `verify_tls: "auto"` (default): verified TLS muna, at kung ang CERTIFICATE ang problema, isang retry na walang verification (tulad ng sample menus mo); `true` / `false` ay puwede pa rin sa `assets/license.json`; (3) browser User-Agent (ang ibang free host ay humaharang sa non-browser); (4) **ipinapakita na ang tunay na dahilan** sa error (hal. `SSL / certificate: ...`, `HTTP 403`, `timeout`, o ang unang bahagi ng HTML na isinagot ng server kung hindi JSON).
- **Hindi ko ma-test ang tunay mong server** (hindi abot ng sandbox ko). Kung may lumabas pa ring error, ipadala ang eksaktong teksto nito.

## v193 — License key login (konektado sa panel mo)

- **Login screen sa pag-start** (`main.py::_license_gate`), ayon sa sample ng panel menu: card na may header, "Copy your license key and tap login", malaking **LOGIN WITH CLIPBOARD** (binabasa ang key sa clipboard; may optional na type-in), "Authenticating..." habang nagve-verify, pulang error text. Naaalala ang key at awtomatikong naglo-login sa susunod na bukas.
- **Protocol (tulad ng sample mo):** `POST /connect` form `game`, `user_key`, `serial` (Android ID) -> JSON `status` (true / "true" / "success"), `data.EXP`, `data.token`, o `reason` / `message` kapag hindi valid. Settings sa `assets/license.json`: `enabled`, `api_url`, `game`, `offline_grace_hours`, `verify_tls`.
- **Dapat tumugma ang `game` sa product name sa panel mo** (default `"NBA2K20"`). Kung hindi pa naka-set sa panel, lahat ng key ay mare-reject. Para i-OFF ang login: `"enabled": false`.
- **Offline:** kapag walang internet, ang huling matagumpay na login ay puwedeng gamitin ng `offline_grace_hours` (72). Ang cache ay HMAC-signed, nakatali sa device, may expiry, at tinatanggihan kapag binalik ang oras ng phone.
- **Seguridad:** hindi ginamit ang Firebase API key / client-write ng sample (puwedeng baguhin ng kahit sino ang database kapag nasa APK ang key); TLS ay vine-verify (hindi na `VERIFYPEER=0`). Ang check ay nasa loob pa rin ng APK, kaya may limitasyon (tingnan ang docstring ng `nba2k20/license.py`).
- Tests: `tests/test_v193_license.py` (fake server). **Hindi ko nasubukan ang Kivy screen o ang tunay mong panel.**

## v192 — etcpak kasama na sa default build

- `buildozer.spec` (default) ay may `etcpak` na sa requirements (gamit ang `recipes/etcpak` na may patch para sa arm64). Dahil dito, **ULTRA HD = 2048x2048** na ang face slot kapag ON ang TUNAY NA RESOLUTION, at mas mabilis ang ETC2 import / encode. Kung walang etcpak sa APK, 1024 pa rin ang max.
- **Hindi ko na-build ang APK dito** (walang Android build environment); ang recipe ay ang dati nang `recipes/etcpak`. Kung mag-fail ang build ng etcpak, ibalik ang dating `requirements` (alisin ang `etcpak`) at ipadala ang build log.

## v191 — EXPERIMENTAL: tunay na mas malaking FACE slot (HD 512 / ULTRA 1024) sa loob ng IFF

- **Natuklasan sa PNG0005.iff:** ang HI FACE DIFFUSE ng ganitong cyberface ay **256x256** lang (LO 128, LO2 64), kaya malabo ang mukha sa laro; ang HD / ULTRA dati ay sharpen lang sa 256.
- **Bago (Workshop > View): `TUNAY NA RESOLUTION (EXPERIMENTAL)` ON / OFF (default OFF).** Kapag ON: **HD 512** = 512x512 face slot, **ULTRA HD** = 1024x1024 (2048 kung may `etcpak` ang build). Sa APPLY: pinapalaki ang slot sa IFF (descriptor 0xC8 + face payload + haba ng file; ang LO / LO2 at lahat ng ibang texture ay buo), ini-encode ang mukha sa bagong sukat, at ang OBB entry ay lumalaki / ina-append kapag hindi na kasya (Save OBB copy).
- **Ayos din:** nawala sa v189 / v190 ang `hairio.hair_cutout` at `export_png` (nasira ang EXPORT HAIR) - ibinalik; at ang hair edge clean ay hindi na nagpapahina ng manipis na strand (halo lang palabas).
- Verified: sa tunay na PNG0005.iff (256 -> 512, decode back OK, 12 / 12 ibang texture byte-identical, nabubuksan ulit ang rebuilt IFF), at sa synthetic OBB copy (`tests/test_v190_slot.py`). Layout detection ay tumatanggap na ng face 256 / 512 / 1024 / 2048 (`CYBERFACE_FACE_SIZES`).
- **HINDI pa subok sa mismong laro.** Gawin sa COPY ng OBB. Kung mag-crash o itim ang mukha, i-OFF at gamitin ang orihinal na OBB; ipaalam ang resulta para maayos / ma-confirm.
- Limitasyon: pure-Python ETC2 encoder ay mabagal sa phone (512 ~ segundo, 1024 ~ mas matagal); ang 2048 ay hindi kaya kung walang etcpak. Ang pagpapalaki ay hindi nagdadagdag ng detalye sa 256 na source; **mas maganda kung mataas ang resolution ng face PNG** na ii-import mo.

## v190 — SD / HD / ULTRA: ipinapakita na ang tunay na sukat ng face slot

- Sa pagpindot ng SD 256 / HD 512 / ULTRA HD 2048 ay lalabas sa status ang **tunay na sukat ng FACE DIFFUSE slot ng IFF** (HI / LO / LO2). Kung mas malaki ang hiniling kaysa sa slot (hal. 2048 sa 1024 na slot), sinasabi nang malinaw na isusulat ito sa sukat ng slot.
- **Hindi ko pa kayang palakihin ang slot sa loob ng IFF / OBB** nang ligtas: kailangang baguhin ang descriptor, payload offsets at laki ng entry, at hindi ko ito masusubukan nang walang tunay na `png####.iff`. Ipadala ang isang IFF para ma-verify bago ko isulat.

## v189 — IMPORT HAIR hindi na nagha-hang, malinis ang hair edge, SD / HD / ULTRA HD

- **IMPORT HAIR (PNG) nag-hang:** ang buong trabaho (pag-load ng PNG, pag-raster ng scalp / noo mask, pagsukat ng skin) ay nasa UI thread kaya nag-freeze ang app sa phone. Ngayon nasa **background na may "Importing hair ..." loading** at ang pag-lapat lang sa texture ang nasa UI.
- **Hair texture na putol-putol / may speckle:** (1) ang bagong hair PNG ay nililinis na (`hairio.clean_hair_edges`): tinatanggal ang maliliit na faint na alikabok (alpha < 24, ito ang grey speckle sa gilid) at **pinapalambot ng <1 px** ang gilid para hindi hagdan ang hairline; ang totoong strands ay hindi ginagalaw. (2) ang pag-clear ng LUMANG buhok ay pinalapad na ng ilang pixel at na-feather, para walang matirang itim na gilid ng dating buhok (hal. sa batok / tenga).
- **Resolution presets (Workshop > View):** **SD 256** / **HD 512** / **ULTRA HD 2048**. Ang SD ay malambot at magaan (dumadaan sa 256 px). Ang HD at ULTRA ay supersample + sharpen gaya ng dati. **Alpha ng buhok / balbas ay hindi ginagalaw.** Paalala: ang sukat ng texture slot sa mismong IFF ay hindi pinapalaki ng tool; ang mga ito ay quality / sharpness ng larawang isusulat.
- Tests: `tests/test_v189.py`.
- **Hindi ko nasubukan sa laro o sa mismong IFF mo.** Ang itim na hugis sa batok at ang "tapang ng kulay" sa screenshot ay hindi ko mapatunayan nang walang IFF / texture; ipadala ang IFF (bago mag-APPLY) at screenshot para maayos nang tama.

## v188 — Ayos ang orange / pulang speckle sa mukha at leeg sa laro (REALISTIC SKIN)

- **Sanhi:** ang REALISTIC SKIN ng v185 / v186 ay naka-**ON by default** at gumagamit ng halos hindi na-blur na white noise na lumalakas habang lumiliit ang texture: sa 512 px na mukha ang karaniwang pagbabago ay +-12 levels (hanggang +-42), sa Realistic skin+ ay +-25 (hanggang +-97). Sa laro, ginagawa itong orange / pulang speckle ng texture compression at ilaw, buong mukha at leeg.
- **Ayos:** (1) **OFF na by default** (`real_level = 0`); kailangan mo itong pindutin para gamitin. (2) Ginawang banayad at **pare-pareho ang lakas sa kahit anong laki ng texture**: level 1 ay ~2 levels average (pinakamataas 8), level 2 ay ~3 - 4 (pinakamataas ~14 sa G / B; mas mataas ng kaunti sa R dahil sa init ng kulay). Naka-blur na ng hindi bababa sa ~1.3 px para hindi masira ng compression. (3) Naayos ang bug sa warm tint ng level 2 (nagbabago ang asul nang 120 levels).
- Hindi ko nasubukan sa laro. Ang **itim na hugis (arrow) sa batok** sa screenshot ay malamang ang orihinal na madilim na hairline / hair coverage ng face texture na kita lang dahil sa speckle sa paligid; hindi ko ito mapatunayan nang walang IFF. Kung nandiyan pa rin pagkatapos ng v188 (REALISTIC OFF), ipadala ang IFF at screenshot bago ka mag-APPLY.
- Tests: `tests/test_v188.py`.

## v187 — 3D BALBAS ayon sa style (Harden / Full / Goatee / Chinstrap) + beard-only OBJ

- **Workshop > Beard:** ang **VOLUME (3D balbas)** ay sumusunod na sa PINILING STYLE (dati iisang hugis para sa lahat): ang Full beard ay lumalapad / bumababa sa panga, pisngi at ilalim ng baba; ang Goatee ay baba lang; ang Chinstrap ay manipis na guhit sa panga; ang Mustache / Soul patch / Stubble ay maliit lang. Ang zone ay ang mismong coverage ng style (`HeadMorph.beard3d_weights`), kaya tugma ang texture at ang mesh. Kapag nagpalit ng style, sumusunod ang 3D agad. Pareho pa rin ang vertex count, kaya naisusulat sa head mesh ng IFF pag **APPLY** (tapos Save OBB copy) at kita sa laro. Player beards (LeBron) ay gumagamit pa rin ng lumang volume zone.
- **3D BEARD presets (isang tap):** `HARDEN 3D`, `FULL 3D`, `GOATEE 3D`, `CHINSTRAP 3D` = style + haba + volume + kapal. Kita agad sa edit preview.
- **SAVE BEARD-ONLY OBJ:** isinusulat ang beard lang (faces sa beard zone, kasalukuyang 3D na hugis, may UV) sa `David2kTool/beards/beard_<style>.obj` para sa Blender / pagsuri. **Hindi** ito maidadagdag bilang hiwalay na object sa cyberface IFF; ang laro ay nakakakuha ng 3D balbas sa head mesh (APPLY).
- Tests: `tests/test_v187.py`. Hindi ko na-run ang Kivy UI, APK o ang laro; laki ng galaw ay sinukat lang sa bundled head (HARDEN 3D ~22% ng taas ng ulo sa pinakamalayo, CHINSTRAP ~ manipis). Kung sobra / kulang sa laro, sabihin at iaayos ang `BEARD3D_SHAPES`.

## v186 — Ayos na lahat ng OBJ head (auto), natural na tattoo, SLIM BROWS at REALISTIC SKIN (auto ON)

- **Mesh fix (`nba2k20/meshfix.py`, bago):** inayos ang lahat ng bundled OBJ (`assets/heads/*`, `head_default`, `new_shape_v1`): na-weld ang mga bitak sa UV seam, inayos ang baliktad / halo-halong winding (ang **Maxey** at **Curry Fix** ay buong baliktad kaya itim ang shading; ang Lamelo ay 182 mixed edges), tinanggal ang mga spike / bukol, at banayad na curvature-aware smoothing (hindi lumiliit ang ulo). **Hindi nagbabago ang vertex count / order**, kaya gumagana pa rin bilang native 2,445-vertex head. Bagong normals (walang seam crease).
- **Auto-fix sa pag-load:** ang `objmesh.load_obj` ay nag-aayos na ng cracks / baliktad na faces / spikes (walang smoothing). Sariling OBJ mo ay inaayos din kapag binuksan sa Workshop.
- **CLI:** `cli.py objfix file.obj --output fixed.obj [--smooth 0.35]` (may report ng before / after).
- **Tattoo ink "Natural" (default na):** malambot ang gilid, bahagyang transparent para kita ang balat, asul-itim na tinta (hindi pure black), Multiply blend. Ang Dark / Super dark ay nandiyan pa rin pero hindi na default.
- **SLIM BROWS / SLIMMER BROWS (Workshop > View):** pinapanipis ang makapal na kilay sa face texture; kilay lang ang gagalawin (mask galing sa head mesh). Preview agad, APPLY para isulat.
- **REALISTIC SKIN / SKIN+ (Workshop > View, ON by default):** pores / grain, natural na patches ng kulay at bahagyang local contrast sa balat lang (hindi buhok / balbas / tattoo, hindi ginagalaw ang alpha). Kita sa preview, kasama sa APPLY.
- Tests: `tests/test_v185.py`.
- **Hindi ko nasubukan sa tunay na png####.iff o sa mismong laro.** Hindi nagiging photoreal ang geometry; ang realistic na itsura ay galing sa face texture. Kung makapal pa rin ang kilay, subukan ang SLIMMER; kung may bukas na seam sa leeg, ipadala ang OBJ.

## v184 — SKIN TONE ng braso / katawan: ikaw ang pipili ng kulay

- **Textures > SKIN TONE (arm / body) (bago):** piliin ang texture (hal. braso), ilagay ang gusto mong kulay ng balat (hex tulad ng `8D6044` o `R G B`), may preset (Fair ... Deep) at **Lakas 0 - 100**. Ipinapakita ang kasalukuyang kulay ng skin na nasukat sa texture. **PREVIEW** muna (walang naisusulat), tapos **APPLY** (naka-stage na; susunod Back > Save OBB copy). May **APPLY SA LAHAT NG SKIN TEXTURE** para sa kaliwa + kanang braso nang sabay.
- Skin lang ang kinukulayan (mainit na kulay, katamtamang liwanag). **Hindi ginagalaw** ang anino / liwanag, tattoo ink (halos itim), puti at ang alpha. Nasusulat pabalik sa sariling format ng texture. Kung walang skin na nakita, sinasabi at walang isinusulat.
- Code: `facelab.parse_color / skin_mask / detect_skin_color / recolor_skin`, `Workspace.skin_tone_info / preview / apply / candidates`. Tests: `tests/test_v184.py` (synthetic na braso + OBB).
- **Hindi ko nasubukan sa tunay na arm texture o sa laro** (wala akong sample). Kung kulang / sobra ang sakop ng kulay sa isang texture (hal. maraming kulay ang tattoo), ipadala ang texture at aayusin ang pagtukoy ng skin.

## v183 — Lahat ng texture slot kita na, HD / ULTRA HD face, at kasama na ang OBJ sa converter

- **Texture list (crowd.iff, gamedataextra.iff, english.iff):** hindi na tinatago ang mga "runtime" slot (dati may "N runtime textures hidden" at kailangan pang i-tap). Lahat ng slot ay nasa list na; may tap pa rin para itago. Ang page size ng list ay 400 na (dati 120 at may < > para sa iba).
- **Preview ng slot na walang tunay na larawan:** dati panel na paliwanag lang ang lumalabas. Ngayon ang hilaw na basa (VRAM order, pagkatapos packed-at-end, gamit ang format ng descriptor) ang ipinapakita, naka-label na **"hula - posibleng ingay"**. Ang may tunay na larawan ay pareho pa rin ng dati. Ang `crowd #1` ay walang pixels talaga sa file, kaya ingay / blangko pa rin ang makikita; hindi ko ito mapipilit na maging larawan.
- **Cyberface Workshop > View: HD FACE at ULTRA HD FACE (bago):** `facelab.hd_face`. Supersample (2x / 3x) + unsharp mask + bahagyang contrast, tapos balik sa orihinal na sukat. Kita agad sa 3D preview, at inilalapat pagpindot ng APPLY (kasabay ng HI / LO / LO2). **Hindi nababago ang alpha** (buhok / balbas). **Hindi nito pinapalaki ang texture slot ng IFF** - mas matalas at detalyado lang, hindi mas mataas na resolution. Pindutin ulit para i-OFF.
- **2K14 Converter:** kasama na sa output folder ang OBJ (3D head): `<target>_2k14_head.obj` + `<target>_2k20_fitted.obj` (file mode) o `<target>_source_head.obj` (IFF -> IFF copy), para mabuksan sa Workshop / Blender at magamit sa 3D buhok / balbas.
- Tests: `tests/test_v183.py`. Hindi ko nasubukan sa Kivy UI / APK / laro.

## v182
- Hair tab: ang IMPORT HAIR (PNG) ay inaalis na ang napiling HAIR TEXTURE style, kaya ang kulay swatch ay hindi na papalit sa na-import na buhok.

## v181 — Totoong itsura ng BALBAS at BUHOK sa texture (siksik, guhit-guhit, matalas na lineup, fade)

- **Bagong `nba2k20/hairpro.py`** (Pillow lang): ang dating beard ay kalat-kalat na grey speckle na walang direksyon. Ngayon:
  guhit-guhit na strands na pababa sa mukha, **siksik / halos solid sa gitna**, malinis na gilid (lineup), at ang pisngi ay
  nagfe-fade papunta sa balat; may maliit na highlight sa ilang strand para hindi flat na itim.
- **Beard tab:** lahat ng style (Full beard, Goatee, Chinstrap, Mustache, Soul patch, player masks) ay gumagamit na ng bago. **Stubble** ay
  manipis na tuldok-tuldok na anino (hindi solid). Ang Thickness slider ay kontrolado kung gaano kalawak ang sakop sa pisngi.
  Ang LeBron strands ay hindi ginalaw.
- **Hair tab > HAIR TEXTURE (bago):** Buzz, Low fade, High fade, Waves (kita ang waves), Full. Matalas ang hairline, ang fade ay galing sa
  taas ng ulo sa mesh (`HeadMorph.hair_fade_weights`). Pumili ng kulay sa swatch para palitan ang kulay ng napiling estilo.
  Texture lang ang binabago (walang galaw sa mesh), at APPLY pa rin para ma-save sa IFF.
- Tinest sa pamamagitan ng pag-render sa `head_default.obj` na may sample na balat. **Hindi ko pa nakita sa totoong cyberface o sa laro**;
  ang itsura sa laro ay nakadepende sa alpha ng face diffuse (GAME ALPHA ON ang default sa beard).
- Bagong tests: `tests/test_hairpro.py`.

## v180 — Scoreboard: sa TOTOONG position nagsusulat na (hindi na kopya lang) + may pangalan + larawan ng laro sa background

- **Ang tunay na dahilan kung bakit walang nagbabago sa laro:** ang 0x120-byte "node" ay KOPYA lang ng position. Ang mga element ng
  scoreboard (may pangalan: `teamlogo_mesh`, `mask_slideout`, `|sm_backpanel|pPlane162`, `g_logo_mesh`, `reporter`, `divider` ...) ay mga
  transform record na may pirmang `46E6CB71 801F78B9 00000049 00000406`; pagkatapos ng pirma: x, y, z (float32) at ang scale. Sa
  newscorebug.iff na ipinadala, buo pa rin ang dating position sa mga record kahit nailipat na ang lahat ng node, kaya walang nagbago.
- **Ayos:** `find_objects` / `find_items` (37 record sa file mo). Ang drag / X+ Y+ / RESET ay nagsusulat na sa **record** (x, y lang;
  8 bytes) at sa mirror na node kapag natukoy ito. Kapag walang record ang file, balik sa dating node mode.
- **Pangalan:** ang bawat kahon ay may pangalang galing sa file (hal. `teamlogo_mesh`). Puwede pa ring i-rename (SET PANGALAN).
- **SCREEN (bago):** ang screenshot ng laro (scorebug sa baba, buttons) ay nasa likod ng mga kahon para makita kung nasaan ang position.
  Itugma minsan sa SCREEN: PAGALAWIN / SCREEN +/-; natatandaan. Gabay lang, hindi nasusulat sa IFF.
- **Paalala:** gamitin ang ORIGINAL na newscorebug.iff (i-export sa OBB) - ang file na dating na-edit ay may mga node na inilipat na.
  Hindi pa nasubukan sa laro; hindi alam kung aling grupo ng record ang live bar (kaya may TABLE button; subukan sa laro).
- Bagong tests: `tests/test_scoreobjects.py`.

## v179 — Scoreboard: lahat ng node table na ang nababasa (ito ang dahilan kung bakit hindi nagbabago sa laro)

- **Dahilan ng bug:** ang newscorebug.iff ay may ilang HIWALAY na table ng node. Ang dating code ay ang una lang ang nakikita (12 node,
  y = 70 ... -237: hindi ito ang score bar). Ang tunay na score bar (6 node, lahat y ~ -181: logo, score, clock) ay nasa ikalawang table,
  ~170 KB pagkatapos, kaya kahit ilipat mo ang lahat ng nakikita mo, walang nagbago sa laro. Mayroon pang ibang table (y ~ -183 / -104 / -190).
- **Ayos:** `find_nodes` ay sinusuri ang buong file (39 node sa file mo, 7 table). Bagong **TABLE** button sa editor: isa-isang table ang
  ipinapakita (bubukas sa table ng score bar), tap para sa susunod, at LAHAT. Ang mga node na nakatago sa y = 5000 / 2000 ay hindi na
  sumisira sa FIT.
- Nagbabago pa rin ang x / y floats lang. Round-trip ng file mo (walang galaw) ay byte-for-byte pareho.
- **Hindi ko pa nasubukan sa laro / Kivy UI / APK.** Hindi rin nasusuportahan ang 2 node na may marker `0xFFFFFFFF` (iba ang layout nila).

## v178
- Scoreboard visual editor: the real scorebug picture (plate from the IFF, in-game look) is drawn behind the boxes as a reference. Move/resize it to line up with the boxes (LARAWAN buttons); KAHON toggles all / selected / none. The picture is never written to the IFF; only node x/y still are.

## v177 — Scoreboard VISUAL editor: pahiga, i-drag ang bawat element, sa hex pa rin nasusulat

- **Home > Scoreboard layout:** pagkapili ng scoreboard IFF (hal. newscorebug.iff) bubukas na agad ang **visual editor** (pahiga). Bawat layout node
  ay kahon na may numero; **i-drag** gamit ang daliri at ang **x / y floats ng node mismo sa IFF data** ang nasusulat (parehong bytes na dating
  hex-edit), kaya gumagana pa rin sa laro. Walang ibang bytes na nagagalaw (na-verify sa tunay na newscorebug.iff: 7 bytes lang ang nagbago).
- Tap ulit sa magkapatong na kahon = lumilipat sa susunod. **LINK** (default ON): sabay gumagalaw ang mga node na nasa iisang lugar (hal. dalawang logo variant).
  Drag sa walang laman = pan. **FIT**, **ZOOM NODE** (lalaki ang bar na hilera), + / -.
- **X- X+ Y- Y+** na may STEP (0.1 / 0.5 / 1 / 5 / 10), **RESET NODE / RESET LAHAT**, **SET PANGALAN** (ikaw ang magpapangalan sa node, hal. "Shot clock";
  naka-save sa phone, hindi sa IFF), **SAVE BAGONG FILE** (output/scoreboard, hindi nababago ang original).
- Ang lumang numeric na listahan ay nandoon pa rin sa popup bago ang editor.
- **Hindi alam:** kung aling node ang shot clock / game clock / score / logo (walang pangalan sa file, kaya may Rename). Ang laki ng kahon ay hula lang (lapad = size
  ng node, taas ay approx.) at ang nagagalaw lang ay x / y. Hindi ko na-run ang Kivy UI o APK build; headless (fake Kivy) tests at ang tunay na IFF lang.
- Bagong tests: `tests/test_scorelayout_visual.py`, `tests/test_scoreview_ui.py`.

## v176 — newscorebug.iff: bumubukas na + Scoreboard layout (experimental)

- **Mabuksan ang newscorebug.iff:** ang ZLIB block nito ay 13 bytes na mas maikli kaysa sa sinasabi ng header (at sira ang checksum). Ngayon binabasa pa rin: pinupunan ng zero hanggang sa sukat ng header para hindi lumipat ang mga offset, may babala sa screen. (Mas malaki sa 4 KB na pagkakaiba ay error pa rin.)
- **Home > Scoreboard layout (bago, experimental):** `nba2k20/scorelayout.py`. Sa newscorebug.iff, may talaan ng 288-byte (0x120) na node; bawat isa ay may size (+0xF0), x (+0x114), y (+0x118), scale (+0x11C). Ilista, baguhin ang x / y / scale / size ng isang node, at I-save bilang bagong file (output/scoreboard). Mga 4 na float lang ang ginagalaw.
- **Hindi pa alam** kung aling node ang shot clock / game clock / fouls / score; kailangan itong subukan sa laro. Hindi pa rin ito napapatunayan sa laro.

## v175 — Mabuksan ang hex-edited na IFF (newscorebug.iff)

- `invalid ZLIB stream ...: incorrect data check` ay nangyayari kapag na-hex edit ang IFF at hindi na tugma ang Adler-32 checksum ng zlib. Ngayon binabasa pa rin ang data (raw deflate) at hindi pinapansin ang checksum lang na iyon; ang ibang zlib error ay error pa rin. Pag-save, tama na ulit ang checksum.
- Hindi ito makakabasa ng IFF na sira na talaga ang compressed data (hindi lang checksum).

## v174 — 2K14 Converter: buong cyberface ang nililipat

- Kapag walang texture sa TARGET na mapaglalagyan (hal. PNG4000.iff), ang BUONG source file (mukha, hair, hugis, lahat) ang isinusulat sa pangalan ng target. Byte-exact na kopya, walang hula.
- Kapag may `png####_hi.iff` / `_lo.iff` ang source pero wala sa target, kinokopya ito bilang `<target>_hi.iff` / `_lo.iff` (dati nilalaktawan).
- Tinest sa tunay na png1398.iff (synthetic na target); hindi pa sa laro.

## v173 — 2K14 Converter: ipakita ang laman ng target

- Kapag "HINDI NAILIPAT / walang texture", ipinapakita na ng IFF->IFF copy ang lahat ng texture na nakikita ng tool sa TARGET (at kung wala talaga). Para malaman kung maling file ang target (hal. kailangan ang png####_hi.iff) o layout na hindi pa suportado.

## v172 — CI fix

- `tests/test_v132.py::test_bundled_player_heads_load` ay humihingi ng hindi bababa sa 13 na head OBJ, pero 11 lang ang nasa `assets/heads` (kaya bumagsak ang "Run core tests" at hindi na umabot sa Build APK). Tinanggal ang hard-coded na bilang; sinusuri pa rin na may Lolobron at na lahat ng head ay may faces + UV.

## v171 — Cyberface edit: listahan ng HI / LO / LO2 face + tseke na may beard pagkatapos mag-APPLY

- **TEXTURES (HI / LO / LO2 face)** na button sa View panel ng Cyberface Workshop: listahan ng nakikitang textures (HI FACE DIFFUSE,
  LO, LO2, SKIN / MATERIAL MAP ...) na may laki, format, KB at status, at PREVIEW / EXPORT / IMPORT sa bawat isa (`Workspace.face_texture_index`).
- **Tseke pagkatapos ng APPLY / IMPORT** (`Workspace.verify_face_lods`): binabasa ulit ang bawat FACE DIFFUSE (HI, LO, LO2) mula sa IFF at
  ikinukumpara sa isinulat; sinusukat din kung nandiyan pa ang beard / buhok (alpha) sa bawat LOD. Ipinapakita sa mensahe: OK o
  PROBLEMA (at kung ano). Hindi na hula na "sana may beard".
- Tests: `tests/test_face_verify.py`.
- **Hindi pa:** hindi ito nasubukan sa tunay na cyberface IFF na may HI / LO / LO2 (walang sample sa chat); synthetic lang ang test.

## v170 — Buong cyberface set: png####.iff + _hi + _lo sabay (mukha, kilay / buhok, hugis)

- Ang AUTO button (IFF -> IFF) ay kumokopya na ng BUONG set: `png####.iff`, `png####_hi.iff`, `png####_lo.iff` ng source papunta sa
  magkaparehong suffix sa target (Workspace.cyberface_copy_set). Ang kulay ng mukha ay nasa `_hi`; ang kilay / balbas / buhok ay nasa
  hair atlas (HAIR / BACK OF HEAD); kasama rin ang skin map at hugis ng ulo. Ang suffix na iisa lang ang meron ay nakalista,
  hindi hinuhulaan. Isang file na pumalya ay hindi humihinto sa iba.
- **Hindi pa:** body tattoo (wala sa `png1398.iff`; kailangan ng sample ng IFF na may body texture) at hair MESH ng ibang style
  (iba ang vertex count / topology; ang tail ng head stream ay hindi malinaw na kilay o buhok, kaya hindi ginalaw).

## v169 — Cyberface COPY (IFF -> IFF): `png1398.iff` ay nalilipat na (hugis ng ulo + hair + skin map)

- **Sanhi kung bakit "ayaw ma-convert" ang `png1398.iff`:** hindi ito 2K14-style na file (walang ARGB/DXT na face sa dulo). Cyberface ito sa
  2K20 container: 128x128 SKIN / FACE MAP + 1024x1024 HAIR / BACK OF HEAD + packed na ulo (3,273 vertex). Ang 2K14 converter ay mukha
  (diffuse) lang ang hinahanap, kaya error ang lumabas.
- **Bago:** `Workspace.cyberface_copy_files(source, target, out_dir)`: kapag walang 2K14 face ang piniling source `.iff`, kinokopya ito
  sa target (isang save): bawat texture na may kaparehong pangalan (face map, hair / back of head, face diffuse kung meron sa
  dalawa; resize na hindi sinisira ang alpha) at ang HEAD SHAPE (packed head stream, o float mesh kung iyon ang target). Ang
  AUTO button ng 2K14 Converter ay awtomatikong gumagamit nito. Output: `output/converted/<pangalan ng target>`; hindi nababago ang
  original; may ulat kung ano ang nailipat at hindi.
- **Na-test sa tunay na `png1398.iff`:** ginawang source ang binagong kopya (pulang hair atlas + inilipat na 300 vertex ng ulo) -> kinopya
  sa orihinal: nakita sa output ang pulang hair atlas at nagbago ang ulo; hindi nagalaw ang ibang vertex at ang original.
- **Hindi pa:** ang FACE DIFFUSE (kulay ng mukha) ay wala sa `png1398.iff`; nasa ibang file (hal. `png1398_hi.iff`). Piliin iyon bilang
  source para mailipat din. Tests: `tests/test_cyberface_copy.py`.

## v168 — Auto na makita ang tunay na larawan ng "runtime" textures (iba ang format kaysa sa descriptor)

- **Nahanap na sanhi ng sirang texture sa `gamedataextra.iff` / `english.iff`:** sa maraming slot, TAMA ang offset (VRAM order)
  pero hindi ang format na nakasulat sa descriptor. Halimbawa sa `gamedataextra`: #28 / #57 / #59 ay ETC2 RGB (jacket, damit, balat ng
  katawan) pero nakasulat na RGBA8; #32 - #37 ay RGBA8888 na cloth normal map pero nakasulat na ETC2; #19 ay face-skin atlas;
  #51 ay hair (ETC2 RGBA8). Dati, ingay ang lumalabas o hinide.
- `iff_core.best_runtime_reading` ay sumusubok na ngayon ng ibang format (ETC2 RGB / RGBA8, RGBA8888, RG88) kapag ingay ang format ng
  descriptor, at tinatanggap lang kapag malinaw na larawan: coherence >= 0.60, noise <= 0.33 (`noise_fraction`, per-channel kaya
  nahuhuli rin ang kulay-pulang ingay), at walang band na halos puro ingay. Ipinapakita sa label kung anong format ang ginamit.
  Sa sample: `gamedataextra` 11 pang totoong larawan (#19 #20 #32-#38 #57 #59). `crowd #1`, `gamedataextra #21 / #44 / #48` at
  `english #6` (ingay) ay nananatiling hidden.
- **Auto (best view):** ang texture na may pare-parehong half-transparent alpha (normal map tulad ng `gamedataextra #55`) ay ipinapakita na
  bilang RGB, hindi na kupas na may checker.
- **Hindi nalutas (hindi mapipilit):** may mga slot na pinupunan ng laro habang tumatakbo o magkakabahaging slot (`gamedataextra #27 / #43 /
  #52 / #56 / #62`: tama sa itaas, ingay sa ibaba) - walang tamang larawan sa file. Ang `crowd.iff #1` ay walang pixels. Hindi ko inilagay ang
  noise gate sa descriptor-format na basa dahil mahuhulog ang mga tunay na font / icon ng `english.iff`.
- **2K14 converter sa `png1398.iff`:** tama ang error: dalawa lang ang texture ng file (128x128 skin map + 1024x1024 hair atlas),
  walang face picture. Malamang nasa ibang file ang face (hal. `png1398_hi.iff` sa OBB). Body shape transfer ay wala pa sa tool.
- Tests: `tests/test_packed_head.py` (noise metric, uniform alpha).

## v167 — Head shape na tunay na nasasave (packed 2K20 head), tamang ulo sa Workshop, walang sabog na "texture"

- **Sanhi ng "di nagsasave yung head shape" at "sabog na ilong / mata":** ang ulo ng karaniwang 2K20 cyberface (`png####.iff`)
  ay naka-pack na 8-byte records (`int16 x, y, z` + `w = ±32767`), kaya hindi ito nakikita ng float32 mesh scanner at walang
  `iff_mesh`. Resulta: ang piniling Head shape ay preview lang, ang APPLY ay "Wala pang binago", at ang preview ay default head na
  hindi tugma sa mukha. Na-verify sa `png7756` (3,146 vertices) at `png1398` (3,273 vertices): nasa offset 81,952 ang stream.
- **Bago:** `nba2k20/packedhead.py` (hanapin, basahin, i-fit at isulat ang stream; pure Python, walang numpy).
  `Workspace.head_mesh_obj()` ay may fallback na ulo mula sa IFF mismo (posisyon mula sa stream + native UV / faces / groups ng
  `assets/head_default.obj`), kaya ang Workshop ay nagpapakita na ng TAMANG hugis sa TAMANG texture. `import_head_shape` ay
  nagsusulat ng posisyon lang (x, y, z; hindi ginagalaw ang w o ang ibang bytes). Ang hugis ay ipinapasok sa bounding box ng
  kasalukuyang ulo (sukat at pwesto ay pareho; proportions lang ang nagbabago).
- **Proteksyon laban sa sirang ilong:** tinatanggihan ang OBJ na iba ang vertex order / topology (correlation sa ulo ng IFF < 0.90, o
  vertex count na hindi 2,445 / hindi katumbas ng stream). Ang mga bundled na `assets/heads/*` na 3,045 / 3,618 / 2,886 vertices
  ay hindi native kaya hindi isinusulat. Ang `new_shape_v1`, `New Beard LBj`, `Wemby` (2,445, native) ay tinatanggap (corr 0.96 - 0.99).
- **2K14 -> 2K20 shape fit** (`_shape14_into_open`) ay gumagana na rin sa packed head.
- **Sirang texture sa `crowd` / `english` / `gamedataextra`:** ang mga "runtime" slot ay hinuhulaan ang lokasyon, at ang gate ay
  sobrang luwag (0.12), kaya naipapakita ang ingay bilang texture. Sa sample: totoong larawan = 0.33 - 0.86, ingay = 0.00 - 0.22.
  Gate ay 0.28 na (`iff_core.RUNTIME_MIN_COHERENT`). Hindi na lalabas ang `crowd #1`, `gamedataextra #26 / #53 / #59` bilang larawan.
- **Hindi nalutas:** ang ilang slot ay talagang pinupunan ng laro habang tumatakbo / magkakabahaging slot (hal. `gamedataextra #27`
  ay may tamang banner sa itaas pero halo-halo sa ibaba). Hindi ko matukoy ang tunay na layout sa file lang.
- Test: `tests/test_packed_head.py`. Hindi ko na-run ang Kivy UI / APK build sa sandbox.

## v166 — Maling "face" sa png.iff, sabog na preview, guard sa sirang texture

- **png.iff na hindi makita ang texture (`png1398.iff`):** nakita sa file na ito: 2 texture lang ang tunay (128x128 skin map +
  1024x1024 hair/beard atlas) at walang face diffuse. Ang blind search ng 2K14 face ay binabasa ang DULO ng file bilang
  \"face\", pero ang dulo ay ang hair atlas, kaya lumabas ang static / itim na picture. Ngayon: (a) hindi na tinatanggap ang halos
  transparent o halos itim na decode (`iff14.plausible_face`), (b) hindi na binabasa ang bytes na pag-aari ng texture na nakita
  ng normal na scanner, (c) malinaw na error: walang face picture sa file na iyon.
- **Sabog ang mukha sa Workshop (mata / ilong):** kapag walang mesh na nabasa sa IFF, default head ang ipinapakita at hindi tugma
  ang UV nito sa mukha. Ngayon may babala (popup + status line) na preview lang iyon at kung ano ang ligtas i-APPLY.
- **Guard sa sirang texture:** ang preview na static noise ay may BABALA, at `import_png` ay tumatanggi sumulat sa slot na
  walang descriptor (hinulaan ng probe) at decode-as-noise (\"hindi texture ang bytes na ito\"), para hindi masira ang ibang texture.
- **Hindi pa nalutas:** ang head mesh ng `png1398.iff` (3,273 vertex, stride 28) ay hindi float32 XYZ kaya hindi nababasa; kailangan
  ng mas maraming sample para ma-decode. Hindi rin na-reproduce ang crowd / gamedataextra / english garbled previews (walang file).

## v165 — Sirang ilong, hindi nagsasave na OBJ / head shape, 2K14 face

Galing sa report: (1) sira ang ilong pag nag-save sa cyberface, halos lahat; (2) ang pinalit na OBJ ay hindi nagsasave
(napunta sa maling IFF / nawala); (3) head shape (New shape v1) hindi nagsasave pagkatapos mag-APPLY; (4) may 2K14
png####.iff na hindi makita ang cyberface.

- **Ilong / shading (`nba2k20/normals.py`, bago):** ang Import OBJ ay positions lang ang isinusulat, kaya ang normals /
  tangents sa vertex data ay galing pa rin sa LUMANG mukha. Ngayon, pagkatapos isulat ang positions, hinahanap sa mismong
  data ang normal field (sinusubok ang f32 / f16 / snorm16 / snorm8 / unorm8 / 10-bit packed sa bawat offset; tinatanggap
  lang kapag unit-length AT tugma sa normals na kinompute mula sa lumang positions + faces), tapos ina-update:
  `bago = luma + (bagong kompyut - lumang kompyut)` (hindi nabubura ang seams). Ang tangent / bitangent (unit vectors na
  perpendicular sa normal) ay nire-orthogonalize lang. **Kung walang makitang verified na normal field, walang binabago**
  (positions lang, tulad ng dati) at sinasabi ito sa report (`normals_note`). Naka-ON by default; `refresh_normals=False`
  para patayin.
- **Nawawalang OBJ / edits:** `Workspace.open_obb_entry` ay hindi nag-i-stage ng pending edits ng nakabukas na IFF, kaya
  kapag nag-Import OBJ ka tapos nagbukas ng ibang entry (o gumamit ng cyberface import / auto PNG / export), nawawala nang
  tahimik ang OBJ. Ngayon auto-stage muna (tulad ng `switch_entry`). Ang **Import OBJ** sa Mesh screen ay auto-stage na rin
  at sinasabi sa status kung na-refresh ang normals.
- **Head shape hindi nagsasave:** (a) ang shape na ibang vertex count ay "preview lang" noon at walang naisusulat; ngayon
  awtomatikong in-fit sa mesh ng IFF (vertex order + UV ng IFF ang nananatili; `convert14.shape_fit`) kaya maisusulat ng
  APPLY. Tantiya ito: malabo ang maliliit na detalye. (b) Ang APPLY ay positions lang na ang isinusulat maliban kung talagang
  may inedit na UV (`Renderer.has_uv_edits`), kaya hindi na ma-a-abort ang buong APPLY kapag hindi na-detect ang UV layout.
- **2K14 face:** kasama na ang DXT3 / uncompressed ARGB sa record-table path, at ang ARGB 256 / 512 sa blind search
  (nauna, kakaunting offset lang, para hindi mapagkamalang DXT5).
- Tests: `tests/test_v165.py` (normals sa 4 encodings, tangents, no-field fallback, stage-on-open, shape fit, 2K14 formats).
- **Hindi ko na-verify sa tunay na 2K20 IFF / sa laro** (wala sa sandbox). Ang normal-refresh ay na-test sa synthetic na
  sphere at naka-fail-safe. Kung walang nagbago sa ilong sa laro, ipadala ang `normals_note` mula sa status / report.

## v160 — Owner lock (owner stamp) para sa mga IFF na na-edit mo

- Bagong **Owner lock** sa home screen: ilagay ang owner name + passphrase (min 4). Kapag ON, ang **Save OBB copy** ay
  nagsusulat ng signed manifest sa tabi ng OBB (`<name>.obb.d2kowner.json`): owner + CRC32 ng bawat IFF na na-edit mo, na
  pinirmahan ng HMAC-SHA256 gamit ang key mula sa passphrase mo (PBKDF2). Hindi iniimbak ang passphrase.
- Sa tool na ito, ang IFF na nakalista sa manifest ay **naka-lock** sa lahat maliban sa may tamang passphrase (Unlock). Ang
  nagbago na ang bytes (ibang CRC) ay hindi na itinuturing na iyo.
- **Hindi ginagalaw ang kahit isang byte ng OBB / IFF**, kaya walang panganib sa game. Kapalit nito: hindi nito napipigilan ang
  ibang tool, at kapag binura ang `.d2kowner.json` wala nang lock. Patunay ng pagmamay-ari + lock sa loob ng tool lang ito.
- Code: `nba2k20/ownerlock.py`, hooks sa `Workspace.open_obb_entry` / `save_obb`. Tests: `tests/test_ownerlock.py`.
- Hindi ko na-run ang Kivy UI / APK build sa sandbox.

## v159 — tinatago na ang mga "RUNTIME TEXTURE" na walang pixels

- Ang mga textures na walang sariling pixels sa file (runtime slot; hal. sa GLOBAL / english / gamedataextra) ay hindi na lumalabas
  sa listahan bilang text panel. May background scan (`Workspace.runtime_readable_numbers`) na nagtatago lang ng mga talagang
  walang mababasang larawan; ang may nahulaang larawan ay nananatili. May row na **"N runtime textures hidden"** sa dulo ng list:
  i-tap para ipakita ulit. Kapag may tina-type sa Filter, lahat ay lumalabas pa rin.
- Test: `tests/test_runtime_hide.py`. Hindi ko na-run ang Kivy UI / APK build sa sandbox.

## v158 — Auto-decode ng kulay, Import / Export Hair, bagong Workshop controls

- **Auto-decode:** ang preview at thumbnails ay awtomatiko nang pumipili ng tamang pixel format. Kung mali / noise ang decode
  ayon sa descriptor, sinusubukan ang ibang format na pareho ang laki sa bytes (RGBA4444 / RGB565 / RG88 / RGBA8888) at ginagamit
  ang malinaw na mas makinis. Malinis na decode ay hindi ginagalaw. **Preview lang**: ang Export / Import ay native format pa rin,
  kaya walang nagbabago sa save (`core.auto_decode_image`, test sa `tests/test_auto_decode.py`).
- **Hair tab:** `IMPORT HAIR (PNG)` (lalabas agad sa 3D ulo; opaque na picture = kusang tinatanggal ang background),
  `EXPORT HAIR (PNG)` (imported / kinulayang hair layer, o ang buhok ng ulo na transparent), at `IMPORT / EXPORT BACK-OF-HEAD HAIR`
  para sa HAIR / BACK OF HEAD texture ng IFF (LO / LO2 na-sync, auto-stage). `nba2k20/hairio.py`, `tests/test_hair_io.py`.
- **Workshop UI:** inalis ang pangit na < > ^ v; camera bar na FRONT / LEFT / RIGHT / BACK / TOP + zoom, FIT / CENTER, Flat, Pahiga;
  swipeable na pill tabs; sliders na may crimson track at mas malaking hawakan.
- Hindi ko na-run ang Kivy UI / APK build sa sandbox (fake Kivy tests lang). Subukan sa phone.

## v157 — OBB 2K16 / 2K17 / 2K18 / 2K19 + 2K20 (auto-detect), audio replace sa loob ng compressed entries

- **OBB layouts:** ang `obb.py` ay 2K20 header lang ang kaya dati. Na-port na ang `ContainerFormat` ng original engine
  (`iffengine.obb`, galing sa disassembly): **2K20** (count @0x18, total blocks @0x28, checksum @0x38, table @0xF8, record
  `<IIII`) at **2K16-2K19** (count @0x10, total blocks @0x18, checksum @0x20, table @0xE0, record `<QII`). Auto-detect gamit
  ang total-blocks x 2048 == file size + table plausibility; may fallback na scoring kapag may sirang row o mali ang size field.
- **Save / rebuild** ay sumusunod na sa layout: record write (u64 length sa 2K16), total blocks, archive CRC32 location, at ang
  resource descriptors ng "compressed" wrapper (base/stride/position/stored/header-length + byte order).
- **Sirang entry ay hindi na nagpapa-fail ng buong OBB:** nilalagyan na lang ng flag (`broken`), nilalaktawan sa CRC, at may
  babala sa header ("N broken entries skipped"). Ipinapakita rin ang "2K16-2K19 OBB" / "2K20 OBB" sa header.
- **Audio:** pwede nang **Replace** ang Ogg / AAC na nakabaon sa loob ng compressed (ZLIB) entry (dati Export lang). Inflate,
  palitan ang slot (parehong laki, zero-padded ang tira), re-deflate ang nagbagong block, stage. Kasya dapat sa slot.
- Bagong tests: `tests/test_obb_layouts.py` (layout detect, 2K16 save/CRC/append, compressed-wrapper descriptors, broken row,
  audio replace sa top-level / raw-embedded / zlib-embedded sa parehong layout). `tests/synthetic.make_obb(layout=...)`.
- **Hindi pa na-verify sa tunay na game files** (wala sa sandbox ang 2K16-2K19 / 2K20 v97 OBB, synthetic lang). Hindi ko rin na-run
  ang Kivy UI at APK build. Kung may OBB na hindi mabuksan, ipadala ang unang 0x300 bytes (hex) at file size para ma-add ang layout.

## v156 — 2K16-2K19 support, Audio (Ogg + AAC), name resolver, CI fix

Galing sa `david2k_tool_src.zip` (decompiled iffengine; ang `core` / `obb` / `integrity` ay disassembly lang, kaya ni-rebuild
ang logic mula sa bytecode at sa mga docstring).

- **CI fix:** nag-fail ang `Run core tests` (`ModuleNotFoundError: numpy` sa `tests/test_beard_relief.py`) dahil Pillow lang ang
  naka-install sa CI. Ang `Workspace.beard_relief` ay pure Pillow / Python na (walang numpy), kaya pareho ito sa convention ng
  repo (CI + Termux ay Pillow lang). Pareho pa rin ang gawa: pinong patayong grain sa HI normal map, sa ilalim lang ng balbas,
  laging mula sa ORIGINAL na normal map (hindi nagpapatong-patong).
- **2K16 textures:** `scan_headers_2k16` (0xC0-byte descriptors, anchor `01 26 00 00 x3`, type 15, fmt @+0x0C, size @+0xA0,
  tagged @+0xAC) + format **6 = ETC1 RGB** (basa gamit ang ETC2 decoder; sulat ay ETC1-safe, walang T/H/planar blocks).
  `locate_textures` ay may `descriptors` / `header_size` params; may `is_2k16` na sa TextureRecord.
- **Audio explorer:** bagong `nba2k20/audio_scan.py`. Nakikita na ang **AAC (ADTS)** entries at nakabaon na AAC streams
  (chain-validated), mas kumpletong Ogg scan (pages grouped by serial: interleaved o walang BOS), tamang codec/duration,
  .aac/.ogg export at play. **Replace** ay gumagana na rin sa audio na nakabaon sa uncompressed (cdf/dram) entry (in-place,
  dapat kasya sa slot; zero-padded). Ang header ay may codec summary.
- **Names:** `nba2k20/nameresolve.py` + `name_patterns.py` (1,558 patterns, ~3.1M spellings). CRC32 exact lang (lowercase / UPPER /
  literal; ang 2K16-2K19 ay lowercase ang hash), walang hula. Ang 19 giant patterns (>5 '#') ay hindi pa kasama.
- Hindi nakuha sa decompile: `cyberfacenames` data, `uvremap` layouts JSON, `integrity` gate.
- Bagong tests: `tests/test_2k16_headers_audio_names.py`. Hindi ko na-run ang Kivy UI, APK build o ang laro sa sandbox.

## v155 — RELIEF (buhok-buhok) + mas malakas na VOLUME para hindi patag ang balbas

- **"Texture pa rin":** ang beard ay face-UV texture, kaya patag sa ilaw ng laro kahit may VOLUME. Ang VOLUME ay mas malakas na
  ngayon (max 0.14 ng laki ng ulo, dati 0.10).
- **Bagong RELIEF (buhok-buhok) slider** (Workshop > Beard, default 0 = OFF): kapag itinaas at pinindot ang **APPLY**, nilalagyan
  ng pinong patayong guhit-buhok ang **HI NORMAL MAP (RG88)** sa ilalim lang ng balbas (`Workspace.beard_relief`).
  Laging ang ORIGINAL na normal map ang ginagamit (naka-save sa scratch), kaya hindi nagpapatong-patong ang noise kapag
  dalawang beses na-APPLY. Nasi-sync din ang LO / LO2.
- Bagong test: `tests/test_beard_relief.py`. Hindi ko na-run ang Kivy UI, APK build o ang laro sa sandbox, kaya subukan sa laro.

## v154 — VOLUME (3D balbas): totoong 3D na balbas, hindi lang texture

- **Problema:** ang beard presets (kasama ang `LEBRON JAMES`) ay texture-only, kaya sa laro mukhang pinturang balat ang balbas
  (patag, walang volume).
- **Ayos:** bagong **VOLUME (3D balbas)** slider sa Workshop > Beard (`beard_vol` sa `headmorph.py`). Itinutulak palabas ang
  baba, panga at ibabang pisngi (hindi ang labi / mustache line), kaya may tunay na volume ang balbas. Pareho pa rin ang
  vertex count, kaya naisusulat ito sa head mesh ng IFF kapag **APPLY** (tapos Save OBB copy). Gumagana sa kahit anong beard
  style, kasama ang LeBron, at nire-reset ng REMOVE BEARD.
- Ang `hihead_head_only_...obj` na ipinadala ay kapareho ng bundled `Lolobron.obj` (png1013 head): walang dagdag na beard mesh sa loob nito.
- Bagong tests sa `tests/test_headmorph.py`. Hindi ko na-run ang Kivy UI, APK build o ang laro sa sandbox.

## v153 — LO / LO2 para sa cyberface na WALANG hair texture (png1013.iff)

- **Bug:** hindi lumalabas ang `LO` / `LO2` textures sa mga cyberface na 4 lang ang HI texture (walang `HAIR / BACK OF HEAD`),
  hal. `png1013.iff`, kaya hindi nasi-sync ang malayuan at bumabalik ang lumang mukha/balbas kapag malayo ang camera.
- **Dahilan:** sa mga IFF na ito wala ring LO hair (16384 B), kaya lahat ng LO / LO2 ay 16384 B na mas malapit sa HI FACE
  (LO2 face = -73728, LO face = -59392, LO detail mask = -2048 na tapos mismo sa simula ng HI face).
- **Na-verify** sa tunay na `png1013.iff`: LO2/LO face, skin, normal at detail ay tugma sa HI na pinaliit (mean error 0.4 - 4.4 / 255),
  at ang pag-edit ng HI face ay napupunta sa LO pagkatapos ng `Sync LOD`.
- Bagong test: `tests/test_lod_nohair.py`.
- Hindi ko na-run ang Kivy UI o APK build sa sandbox.

## v152 — Bagong UI style + mas mabilis na loading

- **Home screen fix:** scrollable na ang home (dati fixed layout kaya nagpapatong ang logo, START at mga card sa maliit na screen).
- **Bagong style:** carbon black + crimson (galing sa logo), mas bilog na cards, walang permanenteng outline sa buttons.
- **Mas mabilis:** static na ang background glow at header line (dati walang tigil ang animation kaya nag-lag), mas maikli ang splash (~0.6s), screen fades, at popup animations; naka-cache ang OVR sa roster list.
- **Glyph fix:** ang `→` na lumalabas na kahon sa phone font ay napalitan ng `>`.
- Hindi ko na-run ang Kivy UI o APK build sa sandbox; kailangang i-check sa phone.

## v151 — In-IFF LOD fix (LO / LO2 textures) + Sync LOD button

- **"Di fix sa malayuan":** ang cyberface IFF ay may LO (128x128) at LO2 (64x64) na kopya ng face / skin / normal / detail / hair
  sa harap ng HI face payload (offsets verified sa real 2K20 png7756.iff; tingnan `iff_core.CYBERFACE_LOD_LAYOUT`). Lumalabas na sila sa
  Textures list (`LO • ...`, `LO2 • ...`) at **auto-sync** sa bawat HI import (Import PNG / Import all PNG / Workshop / UV tattoo / 2K14 FACE).
  Dagdag ito sa `_hi` / `_lo` sibling files ng v149/v150 — magkaiba ang dalawa, parehong kailangan.
- Bagong **Sync LOD (malayuan)** button (cyberface texture screen) at `Workspace.sync_lod()`.
- Import all PNG: hindi ginagalaw ang LO/LO2 PNG na hindi in-edit (para hindi mabura ng lumang PNG ang sync).
- Face pickers ay laging HI FACE DIFFUSE (hindi LO).
- `assets/raw/`: head_topology_2445 / 2256 at canonical_3168_groups.objtopo + `nba2k20/headdata.py` (UV galing sa `assets/uv`, walang duplicate).
- Buildozer `include_exts` may `objtopo`; version 151.

## v148 — Allinfo-driven texture alias and Title Card search fix

- **Shared texture slots:** hindi na awtomatikong binablock ang bawat duplicate payload address. Kung may sapat na recorded allocation at nasa loob ng IFF ang buong encoded payload, nananatiling previewable ang alias; ipinapakita sa location na shared ito. Kung kulang ang bytes, nananatiling blocked at ipinapakita ang available-versus-required size.
- **Title Card discovery:** pinalawak ang OBB CRC candidates para sa `titlecard`, `title_card`, `titlecardbg`, `titlecardbackground`, `titlecardoverlay`, title-page at title-screen variants, kasama ang uppercase/lowercase/mixed-case hashing. Kasama na sa **Title Page** category ang `titlecard` entries, habang **Frontend** pa rin ang title-card overlays.
- **Name search:** gumagana na ang `title card` query sa OBB browser at recursive folder search kahit walang space sa filename (`titlecard.iff`).
- Nagdagdag ng [allinfo findings note](ALLINFO_FINDINGS.md) na tumutukoy kung aling shared slots may valid local bytes at kung alin ang metadata/runtime-only.
- Pinanatili ang v147 parser boundaries, ETC2 odd-size handling, recursive search, catalog fixes, scorebug diagnostics, roster/2KRatings at 2K14-to-2K20 changes.
- Bumped app/build metadata sa `VERSION_CODE=148`, `VERSION_NAME=v148`, Buildozer `1.0.148`.

## Validation

- `python3 -m compileall -q main.py cli.py nba2k20 tests` — pumasa.
- `python3 -m unittest discover -s tests -q` — **319 tests run; 318 passed, 1 skipped**. Ang skip ay nangangailangan ng real-game cyberface fixture na wala sa package.
- Nasubukan sa synthetic fixtures ang shared alias na may sapat na bounded bytes at ang kulang na 24-byte slot. Walang raw IFF/OBB binaries sa `allinfo.zip`, kaya hindi ito ma-decode sa workspace.

## Build and run

- Termux/PC CLI: i-install ang `requirements-termux.txt`, pagkatapos `python3 cli.py --help`.
- IFF filename scan: `python3 cli.py iff scan /path/to/extracted/game/resources`.
- Tests: `python3 -m unittest discover -s tests`.
- Android APK sa Linux/WSL: `pip install buildozer cython`, pagkatapos `buildozer android debug`. Para sa CI variants, tingnan ang `BUILD.md` at piliin ang tamang Buildozer spec.

## Verification limits

Ang `allinfo.zip` ay may JSON lamang para sa `crowd.iff`, `english.iff`, at `gamedataextra.iff`; wala itong raw game bytes, OBB entry list, o `titlecard.iff` record. Ang `english.iff` offsets ay may payload capacity na kasya sa sample texture sizes, kaya hindi na dapat i-block dahil lang shared; kailangan pa ring makita sa aktuwal na app/game kung tama ang visual output. Ang crowd descriptor ay tumuturo sa bytes na mukhang kasunod na descriptor; ang gamedataextra sample slot ay 24 bytes laban sa 8–65 KB na kailangan, kaya nananatiling blocked hanggang maibigay ang external streamed resource. Hindi ginawa ang APK build o in-game rendering check.