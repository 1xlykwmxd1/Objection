# NBA 2K20 OBB / IFF Tool — Android source

Android na bersyon ng `iff_viewer.py` + `obb_tools/*.py` mo. Inalis ang Tkinter,
`.cmd`/`.ps1` launchers at ang Windows `.pyd` sa `vendor/`.

## Laman

| Path | Gamit |
|---|---|
| `nba2k20/obb.py` | dating `nba2k20_obb.py` — basahin ang OBB |
| `nba2k20/obb_rebuild.py` | dating `obb_encrypt.py` — rebuild + CRC32 + verify |
| `nba2k20/direct_obb.py` | direct OBB session (stage / save) |
| `nba2k20/iff_core.py` | lahat ng parser/texture/model/resource logic ng `iff_viewer.py` (walang GUI) |
| `nba2k20/service.py` | `Workspace`: iisang API na ginagamit ng app at CLI |
| `main.py` | Kivy app (touch UI) — ito ang Android tool |
| `cli.py` | Command line para sa Termux/PC |
| `buildozer.spec`, `recipes/` | para i-build ang APK |
| `tests/` | Automated regression suite (synthetic fixtures; walang bundled game data) |

May mga safe parser/preview guard para sa texture boundaries, payload lengths, shared slots,
at mip-chain inference; may synthetic regression fixtures ang mga ito. Tingnan ang `CHANGELOG.md`
at `PATCH_REPORT.md` para sa v147 changes at mga hindi pa na-verify sa real game assets.

## Paraan 1 — Termux (pinakamadali, may CLI)

```
pkg install python python-pillow clang make
pip install -r requirements-termux.txt
python cli.py obb list /sdcard/main.obb --search UA0
python cli.py obb export-png /sdcard/main.obb 12 /sdcard/png
# i-edit ang PNG (huwag palitan ang filename), tapos:
python cli.py obb patch /sdcard/main.obb /sdcard/main_patched.obb --png 12:/sdcard/png
```

## Paraan 2 — APK (Kivy + Buildozer, sa Linux/WSL)

```
pip install buildozer cython
buildozer android debug        # APK sa ./bin
```

Sa phone: buksan ang app → pahintulutan ang "All files access" → Open OBB →
pumili ng IFF → Textures/Models/Resources → Actions → Stage → Back → Save OBB copy.
Lahat ng output ay nasa `/storage/emulated/0/NBA2K20Tool/`
(`patched_obb/` ay may parehong filename ng original OBB).

## Build sa GitHub (walang PC) - tingnan din ang BUILD.md

Push ang folder na ito sa GitHub repo. **Actions > Build APK** (lean, walang ETC2)
ang unang patakbuhin. Kapag gumana, patakbuhin ang **Build APK (with ETC2 native modules)**.
Kung ang second lang ang pumalya, gamitin ang lean APK.

## Auto update (manifest example)

1. Gumawa ng JSON file at i-host sa HTTPS (GitHub raw / release, Cloudflare, atbp.):

```json
{
  "ok": true,
  "versionCode": 96,
  "versionName": "v96",
  "apkUrl": "https://.../David2kTool-v96.apk",
  "apkSha256": "<64 hex ng APK; sha256sum file.apk>",
  "changelog": "Ano ang bago",
  "required": false
}
```

2. Ilagay ang link ng JSON sa `NBA2K20Tool/update_url.txt` sa phone (isang linya), o sa `DEFAULT_UPDATE_URL` sa `main.py`.
3. Tuwing bubuksan ang app may tahimik na check; may "Check for updates" din sa home.
4. Bago ang install: HTTPS lang, SHA-256 dapat tugma, max 1 GiB. Dapat naka-sign ng parehong key ang bagong APK
   (Android mismo ang tumatanggi kung hindi). Itaas ang `nba2k20/version.py` (`VERSION_CODE`) sa bawat release.

## Fixed custom portrait CFID

Range `9000-9999` (`nba2k20/cfalloc.py`). Kapag shared ang mukha ng player, pwedeng gamitin ang libreng custom
CFID na umiiral na sa OBB para sa player na iyon lang. Hindi makakagawa ng bagong OBB entry ang tool, kaya
kailangang may existing na png9xxx entry sa OBB.

## Mga dapat malaman

- **Hindi pa na-build/na-test ang APK at ang Kivy UI** (walang Android/Kivy/internet
  sa pinag-gawan nito). Na-test ang core, service at CLI. Kung may error ang
  Buildozer, kadalasan sa `recipes/` (versions ng `etcpak` / `texture2ddecoder`).
- **ETC2 textures** ay may pure-Python decode at encode fallback (`etc2_dec_py.py`,
  `etc2_py.py`); native `texture2ddecoder` / `etcpak` ay optional para sa mas mabilis
  na trabaho. Sa lean APK, mabagal ang malalaking texture ngunit hindi na hard-block.
- **Android/obb folder**: sa Android 11+ madalas hindi ma-access ng ibang app ang
  `Android/obb`. I-copy muna ang OBB sa Download/internal storage, i-edit doon, at
  ibalik gamit ang file manager na may access (o root/Shizuku/ADB).
- Mag-backup ng original OBB. Kailangan ng free space na kasing-laki ng OBB habang nagse-save.
- Para sa sarili/offline mong game files ang tool na ito; walang game data sa project.

## Test / command-line run

```
python3 -m compileall -q main.py cli.py nba2k20 tests
python3 -m unittest discover -s tests
python3 cli.py --help
```

For recursive IFF filename search from the Android UI, choose **Search IFF folder** on the home screen,
select the root folder containing extracted game resources, then search by exact or partial filename/path.
The scan is recursive and runs in the background; access errors are shown as a partial-scan warning.
Title-name search ignores spaces and punctuation, kaya `title card` ay makakahanap ng `titlecard.iff`.
Build APKs on Linux/WSL with `pip install buildozer cython` then `buildozer android debug`; see `BUILD.md`
for the GitHub Actions/variant build options. Real game IFF/OBB files are not included in this source package.


## Bagong UI (v1.1)

- Dark theme, rounded buttons, two-line list rows, malaking preview na may tamang aspect ratio.
- **IFF browser**: search + category filter (All IFF, Favorites, Court, Logo, Title Page, Frontend,
  Loading Flows, Jersey, English Bootup, Other). Sa "All IFF" view, naka-group ang mga IFF at
  **nasa sariling group sa dulo ang Logo**. Star = favorite (naka-save sa app).
- Sa loob ng IFF: **IFF List** button (sa taas) = side drawer ng lahat ng IFF ng OBB. Kapag
  lumipat ka, auto-stage ang edits ng dating IFF.
- **Auto resize**: Import PNG / Import all PNG ay awtomatikong nire-resize (LANCZOS) sa eksaktong
  size ng texture, kahit ano ang size ng PNG mo.
- Texture list may filter (number / size / format).
- Ang categories ay base sa file name (`iff_category()` sa `nba2k20/service.py`). Ang entries na
  hindi kilala ang pangalan (hash lang) ay napupunta sa "Other" - i-edit ang rules doon.


## v1.3 - Textured 3D preview (Models tab)

- Piliin ang model, tapos piliin ang texture sa **Textures** tab - makikita agad ang texture sa mukha/model.
- **Swipe** sa preview para i-ikot; may Left/Right/Up/Down at Zoom -/+.
- **Open PNG** = i-preview ang kahit anong PNG (hal. bago mong face texture) bago mo i-import.
- **Use tex** = gamitin ulit ang napiling texture (kasama na ang na-import mo).
- **Flip V** kapag baliktad ang texture; **UV** = subukan ang susunod na UV layout.
- Ang UV ay *auto-detected* (hindi alam ng parser kung saan ang UV sa vertex): sinusubukan ang
  f32 / f16 / u16 at pinipili ang mukhang tunay na UV. Kung mali ang itsura, pindutin ang **UV**.
- Code: `nba2k20/preview3d.py` (pure Python + Pillow, walang numpy/GPU).

## Cyberface (OBB screen > Cyberface)
Find an entry by CFID, IMPORT / REPLACE a cyberface IFF, EXPORT the cyberface IFF, or
AUTO PNG (a PNG of any size is resized and written into the biggest importable texture).
OBB entries are identified only by a hash of their file name, so a CFID is resolved by
hashing likely names (CF1013.IFF, CF_1013.IFF, CYBERFACE1013.IFF ...). If nothing is
found, type the exact name in the pattern box ({id} = the number), or use '#entry' /
'hash:XXXXXXXX'. Nothing is written to the original OBB; use Save OBB copy.


## v12 - Cyberface (PNG####.iff) ayos

- Ang 5 textures ng cyberface (Face Diffuse, Skin/Material, Detail Mask, Normal RG88, Hair)
  ay nakikita at na-eedit na: lahat ay may Export/Import PNG at auto-resize.
- **ETC2 import gumagana na kahit walang etcpak** (built-in pure-Python encoder, `nba2k20/etc2_py.py`,
  hanggang 1024x1024; ~1 segundo bawat 256x256). Kapag may etcpak (full build) iyon ang gagamitin.
- Bug fix: dati nawawala ang 5 textures kapag nag-import ka ng normal map na hindi flat ang gilid
  at nag-Stage / nag-reopen. Inalis ang pixel check; structural check na lang.
- Kung may bagong build na hindi kailangan ang `cyberface_build.py`: nasa iff_core.py na ang patch.

## v14 (v13 + your logo, Blender+AI in Textures tab, internet check)
## v13 additions
- David2k Tool header on every screen, "David2kTool loading..." overlay, icon and splash.
- Models tab > Blender export / Blender import (OBJ + UV + MTL + PNG textures + import script).
- Models tab > AI Assist (needs internet + your own Anthropic API key): the AI only returns
  numeric adjustments (colour / brightness / shift / scale); you review before importing.


## v15 - AI Assist na AUTO (walang API key, walang internet)
- AI Assist ay built-in at offline na: hindi na kailangan ng API key o WiFi/mobile data.
  Nagbabasa ito ng sinasabi mo (English o Tagalog: "mas maputi", "mas maitim", "warmer",
  "cooler", "more contrast", "center", "bigger", "rotate left", "slightly ...") at ng
  reference photo (auto skin-tone match). Hindi ito language model - rule + color analysis lang.
- Auto-run pagbukas ng popup; may chips (Lighter, Darker, Warmer, Cooler, Contrast, Center,
  Bigger, Smaller) na nag-aapply agad. Laging may preview bago ang Import.
- Ang Anthropic API key ay optional na lang ("Online AI" button); kapag pumalya, babalik
  sa offline assist.

## v16 - UV Editor (tattoo / overlay)
- Textures tab > **UV Editor (tattoo)**: pumili ng face/skin texture, **Add overlay** (PNG ng tattoo/logo),
  i-drag para ilipat, pinch para i-resize at ikutin, hilahin ang kanto para i-resize.
- Size presets: Maliit / Medium / Malaki / Pinakamalaki. Opacity slider. Blend: Normal / Multiply /
  Overlay / Screen. Rotate -5 / 0 / +5. + Zoom / - Zoom / Reset.
- APPLY = ini-import sa texture (gamit ang built-in encoder), tapos Actions > Stage / Save gaya ng dati.
  CANCEL = walang nagbabago. Offline lahat. Hindi pa kasama: Sync 3D at Change skin tone
  (gamitin ang AI Assist para sa skin tone).

## v17 - Cyberface Workshop
- Textures tab: press the preview image -> **EDIT (Cyberface Workshop 3D)**, or the "EDIT" button; Models tab also has a Workshop button.
- Smooth textured 3D head (generic head, or **Open OBJ** for your own model) with live changes; drag = rotate, two fingers = zoom, "Flat" = 2D texture view.
- Tabs: View / Tattoo (stamps + your PNG, size, rotate, opacity, blend, colour, delete) / Paint (brush, erase) / Skin (presets, brightness, saturation, warmth, strength).
- Undo / Redo, **APPLY** writes into the selected texture (then Actions > Stage / Save, then replace in OBB).
- OBB IFF list: search, categories (Court, Logo, Title Page, Frontend, Loading Flows, Portrait, Jersey, English Bootup, Cyberface, Custom, Other), Favorites, counters, and a toggle to show ALL OBB entries (not only IFF).
- Tests: `python tests/test_core.py`, `python tests/test_workshop.py`, `python tests/test_workshop_ui.py`.

## IFF mesh UV writeback + supplied UV references

- OBJ export now includes the detected UV layout (`f16@offset`, `f32@offset`, or
  `u16@offset`) as metadata. Blender/Workshop OBJ import writes edited UVs back to
  that exact field while preserving positions, normals/tangents, skin weights,
  bone indices, and topology unless those parts were intentionally edited.
- The importer rejects ambiguous UV layouts, missing per-vertex UVs, conflicting
  split seams, non-finite values, or a changed vertex count instead of guessing.
- `assets/uv/` contains the supplied 2445-vertex native UV and 3213-vertex
  cyberface UV references. The 2445 map replaces the UV coordinates in
  `assets/head_default.obj`; Workshop can load the matching reference map from
  **LOAD SUPPLIED UV REF**. The 3213 map is offered only when the vertex count
  matches; use it only with the matching vertex order. Undo is available before
  APPLY, and APPLY stages/saves the changed IFF as usual.
- OBJ UV reference files are user-provided coordinate data; the supplied sample
  game IFF and decompiled Java reference archives are not copied into the APK.


## UV Grid Maker (v38)

`nba2k20/uvgrid.py` — grid sa ibabaw ng image/mukha → flattened PNG, overlay PNG, OBJ at JSON.
Sariling implementation (hindi galing sa ibang app). CLI:

```
python cli.py uv face.png out_folder --grid 12x12 --move 6,6,0.55,0.45
python cli.py uv face.png out_folder --load out_folder/face_grid.json
```

- `--move COL,ROW,X,Y` = ilipat ang isang point (x/y 0..1, y pababa). Pwedeng ulitin.
- OBJ: `v` = regular na plane, `vt` = edited grid. Nababasa ng sarili nating OBJ loader.
- JSON keys: `grid`, `imageWidth`, `imageHeight`, `mode`, `rotation`, `vertices[{i,u,v}]`.
- Wala pang touch UI sa Kivy app para dito (core + CLI + tests lang).


## v51 - Frontend Legacy (2K logo) = RGBA4444 fix + OBJ inspect
- **Bug**: sa NBA 2K27 build, RGBA4444 ang binabasa ng laro sa 2K logo (Frontend Legacy), pero RGB565 ang isinusulat
  ng tool. Resulta sa laro: puti = pink/dilaw, pink = orange, navy = itim, speckles sa glow.
- **Fix**: Textures > Import PNG sa "Frontend Legacy (2K logo)" ay may **format chooser**:
  *RGBA4444 (transparent bg - 2K27)* / RGB565 black / RGB565 white. Pumili ng RGBA4444.
  - Ang itim na background na konektado sa gilid ay ginagawang transparent (soft edge sa glow); ang itim sa loob ng logo
    (outline ng letra) ay nananatiling opaque. Floyd-Steinberg dither para walang banding.
  - Awtomatikong tinutukoy ng tool ang format kapag nabuksan ulit ang IFF (`detect_legacy_pixel_format`), at kaya
    nang hanapin ang logo band sa RGBA4444 data. **Pero** kung RGB565 na ang naisulat dati sa IFF mo, hindi iyon
    makikita ng auto-detect - pumili ka lang ng RGBA4444 sa chooser at i-import ulit ang PNG.
  - Code: `iff_core.encode_rgba4444(dither=)`, `key_out_background`, `import_png(as_format=)`.
- Mesh tab: **INSPECT MODEL** (vertices/triangles/UV/normals/degenerate faces).


## LeBron thick beard

Sa **Beard** tab, piliin ang `LEBRON JAMES` para sa naka-bundle na full-beard mask. Auto-set ito sa
thickness 1.0, warm dark-brown hair grain, at **GAME ALPHA ON**, para makita ang beard sa face preview
at ma-export ang facial-hair alpha sa game texture. Pindutin ang **APPLY**, pagkatapos **Stage** at
**Save OBB copy**. Ang `LEBRON JAMES` preset ay texture-only; hindi nito inililipat ang chin mesh. Para sa totoong 3D na balbas gamitin ang
**VOLUME (3D balbas)** slider (v154): itinutulak nito palabas ang baba / panga at isinusulat sa head mesh ng IFF sa APPLY.

**v134 fix:** kapag binuksan ang Cyberface Workshop habang naka-select ang ibang cyberface map
(hal. `HAIR / BACK OF HEAD` o `SKIN / MATERIAL MAP`), awtomatikong lilipat ito sa `FACE DIFFUSE`.
Ang beard at hairline ay face-UV texture layers; dati puwede silang maisulat sa maling texture at
mukhang walang nangyari sa laro. Pagkatapos ng APPLY sa OBB, kailangang i-save ang **OBB copy** at
palitan ang game OBB gamit ang output na iyon.

Ang **HABA (Length)** slider / SHORT - MEDIUM - LONG buttons ay para sa generic beard styles. Binabago
nito ang chin/under-chin mesh at pinalalawak ang texture mask. Ang OBJ export ay para sa Blender;
ang mesh export ay hindi sinusulat sa game IFF.

**Hair coverage:** ang face diffuse ay may hair coverage sa ALPHA (mababa = balbas). Kapag pinili ang
player-style beard, ibinabalik sa ON ang `GAME ALPHA (hair mask)` at isinusulat ang hair coverage kasama
ng kulay.

**Natural density:** pinalakas ang multi-scale brown strand contrast sa full thickness upang hindi
magmukhang flat black paint. Pinananatili ang LeBron mask contour at feathered edge upang maiwasan ang
rectangular patch.

## scan_faces.py (v1.5)

Hanapin ang mga face texture na may balbas sa OBB (read-only): `python scan_faces.py /sdcard/<obb> --out /sdcard/Download/faces` -> `faces.csv` + `sheet_XX.png` na may entry index.

## Roster Editor (v77) - pure Python, no Java

Third home button, separate from Open OBB / Open IFF. Loads a roster file, lists teams and
players, edits ratings (25-99) and saves a NEW copy to `/storage/emulated/0/David2kTool/roster/`
(the original roster file is never overwritten; the saved copy is decoded again and compared
before it is published).

- Engine: `nba2k20/roster_core.py` (container + crypto + player/team table parser + rating access).
  It is a mechanical Python translation of the AkoSiMC v37.0 Roster* classes with hand-optimised
  hot loops (fast cipher, bit scan). No Java, no `android.add_src`, no pyjnius needed.
- The fast cipher and bit-scan routines were verified byte-for-byte against the translated
  originals; `tests/test_roster.py` runs a synthetic container round trip + rating edit + save.
- NOT included: Manual OVR / Online Ratings sync (not present in the v37.0 source).
- Not tested against a real NBA 2K20 roster file in this environment: test on a COPY first.
- Loading a large roster takes some seconds on a phone (pure Python decrypt + inflate).

## Online ratings sync (v97)

Roster Editor > player > **Sync online ratings (type any name)**, o **Sync team online** sa player list.
- Source: 2kratings.com. Port ng `OnlineRatingsClient` (27 ratings na may katapat sa roster file).
- Kahit anong name ang puwede: custom, nickname, Jr./Sr., accents, slug, o buong 2kratings link. Sinusubukan ang
  ilang spelling (hal. `gary-trent-jr` -> `gary-trent`) hanggang may makita.
- Hindi ginagalaw: jersey, portrait/CF, name, at mga rating na wala sa site (Shoot In Traffic, Awareness, Emotion...).
- **Match OVR** (optional) = gagamit ng Manual OVR para tumama sa online OVR (nag-shift ng lahat ng ratings).
- Wala pa: tendencies at badges (hindi pa kilala ang field offsets sa roster file). Hindi pa na-test sa totoong network/device.

### v103 additions
- Sync team online ay may FULL AUTO na (galing sa Java src: move/release/assign player ay mekanikal na na-translate sa `nba2k20/roster_edit.py`): kinukuha ang kasalukuyang roster ng team mula sa 2kratings, tina-trade ang mga player sa team, ang mga hindi nahanap sa roster ay pinapalitan ng pangalan ang sobrang player ng team (kung kasya ang pangalan), isinusulat ang ratings, at dina-download ang portrait PNG at nilalagay sa OBB sa libreng custom CFID. Hindi nagse-save: SAVE AS NEW at Save OBB pagkatapos. Ratings-only mode ay nandiyan pa rin.

### v102 fixes
- Online sync ngayon ay kapareho ng original Java app: Android HttpURLConnection muna (parehong headers), WebView lang kung 403 pa rin. Ang WebView ay naghihintay na ng fully-loaded at stable na page (dati partial DOM = "not found online"). Ang team report ay may reason na bawat player.

### v101 fixes
- Online sync ay auto na: ang hidden WebView ay full-size na naka-park sa labas ng screen (parang normal na tab) kaya kusang pumapasa ang Cloudflare check. Ang "verify" screen ay lalabas na lang pagkatapos ng 60s bilang huling paraan.

### v100 fixes
- Online sync WebView: may WebViewClient na (hindi na lumalabas sa browser ang redirect), Chrome user-agent, at kapag hindi natapos ang Cloudflare check sa loob ng ~12s, lalabas ang WebView nang full screen para i-tick mo ang "verify you are human" (isang beses lang; naka-save ang cookie). Kapag nag-timeout, may diagnostics na sa error (href, html size, title).

### v99 fixes
- Online sync: 403/429/503 mula sa 2kratings (Cloudflare) ay may fallback na: urllib -> Android HttpURLConnection -> hidden WebView (totoong Chrome engine). Browser-like headers na, wala na ang "David2kTool" sa user-agent, at may 0.8s pagitan ng bawat player sa team sync.

### v98 additions
- Tendencies + legacy badges are now fetched from 2kauction (port ng `parse2kAuctionHtml`) at lumalabas sa sync result.
- **Hindi pa isinusulat sa roster** ang tendencies/badges: wala sa `roster_core.py` ang bit offsets. Punan ang
  `TENDENCY_BITS` sa `nba2k20/online_ratings.py` kapag alam na ang offsets (huwag manghula, masisira ang roster).
- Custom names: natatandaan ang name -> 2kratings page sa `NBA2K20Tool/online_aliases.json`, kaya gumagana ang Sync team
  kahit custom ang pangalan sa roster. Puwede mong i-edit ang file na iyon.

### v98 fixes
- `online_ratings.extract_range_value`: line-start match muna bago mid-line, para hindi mapagkamalan ang "Foul" bilang "Hard Foul" (at "Drive" bilang "Post Drive"). May bagong `tests/test_online_ratings.py`.
- Naayos ang version: `version.py` at `buildozer.spec*` ay v98 na (dati v96, kaya mali ang update check).
- Tendency layout: bit = 3490 + index*8 (8 bits, mula sa `RosterEditor$TendencyField`). Kulang pa: label->index table at value encoding (`TENDENCY_INDEX`, `TENDENCY_ENCODE`). Badges: wala pa ring offsets.
- v98: sync_team ay hindi na nagtatago ng error. Network/TLS/403 ay hihinto agad at ipapakita ang dahilan; "not found online" ay para na lang sa totoong 404. Sinusubukan ang certifi, default at Android system CA store.

## Strand beard (totoong balbas) galing sa cyberface IFF
Sa PNG####.iff ng mga player na may totoong pahabang balbas (hal. `PNG1013` = LeBron) ang balbas ay nasa
**HAIR / BACK OF HEAD** texture (2048x2048, alpha = buhok), hindi sa face diffuse.

    python tools/beard_transplant.py extract PNG1013.iff out "LEBRON JAMES" --bundle   # PNG ng balbas (transparent)
    python tools/beard_transplant.py apply PNG1013.iff TARGET.iff PNG_TARGET_BEARD.iff [--part beard|mustache|both] [--over]

Pangalanan ang output na may `png<number>` (hal. `PNG1013_BEARD.iff`) para makilala ng tool ang hair texture.
Naka-bundle: `assets/styles/strands_LEBRON JAMES.png`. Inayos din ang `tools/make_style.py` (dati nag-e-error
na `StopIteration` sa IFF na walang FACE DIFFUSE; ngayon kinukuha na nito ang strands).

**Workshop > Beard tab:** ang `LEBRON JAMES` ay gumagamit na ng totoong strands (`assets/styles/strands_LEBRON JAMES.png`,
beard lang) na nilalagay sa face UV sa loob ng lugar ng beard mask niya. Gumagana ang Thickness at Beard color
(kulay-tint na may natitirang grain ng buhok), at ang GAME ALPHA ay auto-ON. Para sa ibang player:
`python tools/beard_transplant.py extract PNG####.iff out "NAME" --bundle` (kailangan din ng `beard_NAME.png` mask
para sa eksaktong lugar; kung wala, gagamitin ang karaniwang lugar ng balbas).

**Face UV controls (Beard tab, strand styles):** Kaliwa/Kanan, Taas/Baba, Laki (Size), Lapad (Width) at RESET FACE UV
para tumama ang strands sa panga/baba ng kahit anong mukha. Isang undo step bawat galaw ng slider.

## 2K14 -> 2K20 cyberface (2K14 Converter)

Hiwalay na screen sa home: **2K14 Converter**. Walang gagalawin sa OBB mo hanggang hindi mo tinatap ang "Save OBB copy".

1. **FACE -> 2K20 CYBERFACE** (kailangan ng bukas na OBB): ilagay ang CFID ng 2K20 cyberface, tapos piliin ang
   2K14 cyberface `png####.iff` (o DDS / PNG). Ang face diffuse ay ilalagay lamang sa natukoy na `FACE DIFFUSE`
   ng 2K20. Pinananatili ang alpha/mask; kung walang label at higit sa isang texture ang puwedeng pagpilian,
   hihinto ang converter sa halip na hulaan na texture #1. Ire-resize lang kung halos magkapareho ang aspect
   ratio; tatanggi ito kung magkaiba para hindi ma-stretch/crop ang mukha nang walang UV mapping.
2. **PREVIEW / EXPORT 2K14 FACE PNG**: tingnan ang face ng 2K14 IFF at i-save bilang PNG (`David2kTool/png`).
3. **HEAD SHAPE**: piliin ang 2K14 head OBJ (hal. `HEADKD.obj`). Inililipat ang vertices ng
   `assets/head_default.obj` papunta sa hugis nito. Pareho pa rin ang vertex count / order / UV / faces ng 2K20 head.
   Output: `David2kTool/obj/<pangalan>_fit.obj`. Strength 0-1 (default 1).

CLI (Termux):
- `python cli.py iff14 png8773.iff --output face.png`
- `python cli.py face14 PNG0934.IFF png8773.iff --output PNG0934_KD.IFF` (puwede ring DDS / PNG; `--texture N`)
- `python cli.py shapefit assets/head_default.obj HEADKD.obj --output head_kd_fit.obj` (`--strength 0.7 --smooth 3 --scale 1.05 --dy -0.2`)

Paano nababasa ang 2K14 IFF (format assumptions verified earlier against `png8773.iff`): normal na "2K compressed
IFF" ito; bawat texture ay may 0xF0-byte record at ang pixel data ay nakaayos sa dulo ng decompressed stream.
Ang parser ay nagbabasa ng DXT1/DXT3/DXT5/A8R8G8B8 at sinusuri ang decoded image bago tanggapin. Ang converter
na ito ay **hindi** naglilipat ng hiwalay na AO, tattoo, normal, neck/body texture o 2K14 mesh, at **hindi**
gumagawa ng 2K14-to-2K20 UV remap. Kailangan ang aktuwal na source at target assets para matukoy at mapatunayan
ang mga iyon; huwag ipagpalagay na pareho ang UV atlas ng lahat ng player.

## v143 - Runtime textures (english / gamedataextra / crowd IFF)

- Textures na walang sariling pixels (tag = 1, "runtime / streamed") ay hindi na puting kahon + Error popup.
  Placeholder panel na ang lalabas at may hash bilang pamagat sa listahan.
- Bagong `Dec: Seq VRAM (try)`: binabasa ang VRAM block ayon sa descriptor order (may mip chain). Sa
  gamedataextra.iff lumalabas dito ang totoong face/jersey/logo textures; ang iba ay noise (runtime slot).
- Ang `Dec: L8 / RGB565 / ETC2 ...` ay gumagana na rin sa runtime slot (gamit ang parehong guess na offset).
- Export/Import PNG ay hindi pa rin gumagalaw sa mga runtime slot (preview lang) para walang masira.
