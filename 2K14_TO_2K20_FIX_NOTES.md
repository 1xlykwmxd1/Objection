# 2K14 → 2K20 conversion fix notes

## Mga naayos na source-code risks

- **Target texture:** Dati, kapag hindi mahanap ang label na `FACE DIFFUSE`, pumipili ang converter ng texture #1 kahit multi-texture ang cyberface. Maaari itong maging skin/material map, detail mask o ibang asset. Ngayon, ginagamit ang labeled face diffuse; kung iisa lang ang decodable texture, maaari itong piliin dahil walang ambiguity. Kung marami at walang malinaw na face label, humihinto ito at walang binabago.
- **Aspect ratio:** Dati, nire-resize ang source face image sa anumang target dimensions, pati magkaiba ang proportions. Ngayon, pinapayagan lang ang resize kung halos magkapareho ang aspect ratio; kung hindi, nagbibigay ito ng error sa halip na mag-stretch/crop nang walang verified UV remap.
- **Face alpha:** `FACE DIFFUSE` alpha ay game mask/hair-coverage data, hindi logo transparency. Hindi na dumadaan ang face diffuse sa automatic background key-out. Sa generic face import, RGB at alpha/mask ay nire-resample nang hiwalay; hindi pinapalitan ng premultiplied transparency handling ang mask values.
- **Batch resource handling:** Isinasara na ang source/fitted image buffers kada conversion para hindi lumobo ang memory habang nagko-convert ng maraming mukha.
- **Zoom:** Sinuri ang Workshop zoom. Ang zoom state ay hindi nire-reset ng tab switch o preview refresh; reset lang sa `Reset view`/`FIT / CENTER`. Nagdagdag ng regression test para rito. Hindi ako nakapag-reproduce ng reset bug sa source na ito.
- **Docs:** Nilinaw sa README na face diffuse lang ang kasalukuyang 2K14 conversion. Walang pangakong naililipat ang hiwalay na neck tattoo/AO/normal texture o na na-remap ang UV.

## Nasubukan

- `python3 -m compileall -q main.py cli.py nba2k20 tests` — pumasa.
- `python3 -m unittest discover -s tests` — **303 tests passed, 1 skipped**.
- May regression tests para sa mismatched aspect ratio, ambiguous target texture, opaque face-alpha preservation at Workshop zoom persistence.

May ilang dating deprecation/resource warnings at expected Android mock stack traces sa suite output; hindi sila nagpa-fail ng tests.

## Hindi pa mapatutunayan nang walang aktuwal na game assets

Wala sa uploads ang aktuwal na 2K14 `.IFF`/`.DDS`, 2K20 `.OBB`/target cyberface IFF, 2K14/2K20 head mesh pairs, o in-game screenshots. Kaya hindi pa napatutunayan ang DXT→target-game decode, player-specific UV correspondence, magkakahiwalay na tattoo/neck texture assignment, o in-game result. Ang kasalukuyang code path ay naglilipat lamang ng pangunahing face diffuse; hindi nito inililipat ang hiwalay na AO, tattoo, normal, neck/body texture o 2K14 mesh, at wala itong 2K14-to-2K20 UV remap.

Para makumpleto ang UV/tattoo/in-game fix, kailangan ang source `png####.iff` o DDS na may problema, ang target NBA 2K20 OBB (o extracted target cyberface IFF), at kung mayroon, source/target head OBJ o UV references. Magdagdag ng screenshot/render ng source at resulta sa game. Gamitin ang OBB copy; huwag ibigay ang original lang kung ayaw mong ma-overwrite. Hangga't wala ang assets na iyon, hindi dapat maghula ng mapping o maglipat ng tattoo pixels sa arbitrary atlas location.
