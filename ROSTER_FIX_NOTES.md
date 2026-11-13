# Roster at online ratings fix — David2KTool v146 source

## Naayos sa online ratings update

- Ang rating extraction ay limitado na sa **kasalukuyang NBA 2Kxx Attributes section**. Hindi na nito kukunin ang parehong label mula sa bio text, historical ratings, o ibang player-version section. Kapag hindi makilala ang current attributes block, walang ratings na isusulat (fail-closed).
- Mas mahigpit na ang player identity check. Kailangan tumugma ang first at last name, kasama ang common short forms at suffix/middle-name variants; hindi na sapat ang apelyido lang. Iniiwasan nito ang paglalagay ng ratings ng ibang player na pareho lang ng apelyido.
- Nagdagdag ng regression tests para sa maling duplicate ratings sa labas ng current table, nawawalang table boundary, at maling page na kapareho lang ng apelyido.
- Binago ang online page fixtures sa tests para sumunod sa kasalukuyang 2KRatings format.

## Napatunayan sa live 2KRatings page

Binuksan ang kasalukuyang Joel Embiid page at pinatakbo ang David2KTool parser sa nakuha nitong HTML. Tumugma ang heading na **Joel Embiid**, OVR na **91**, at **27 mapped rating fields**; kabilang sa nabasa ang Close Shot **94** at Three-Point Shot **79**. Hindi ibig sabihin nito na lahat ng lokal na 2K20 roster attributes ay napupunan: 27 lang ang kasalukuyang online-to-roster map. Ang fields na walang katumbas sa source ay sadyang hindi hinuhulaan at mananatiling hindi nababago.

Ang OVR na ipinapakita ng editor ay estimate nito mula sa roster attributes, hindi ang opisyal na in-game OVR formula. Hindi awtomatikong binabago ang attributes para piliting tumugma sa online OVR, dahil puwedeng baluktutin nito ang player ratings.

**Network note:** Direct HTTP request mula sa sandbox ay nakatanggap ng 403 mula sa 2KRatings. Na-load naman ang public page sa browser at nasubukan ang parser sa page HTML na iyon. Hindi ko na-run ang Android app sa aktuwal na phone/Android WebView sa environment na ito; ang app-side fallback behavior ay kailangan pang i-verify doon.

## Tungkol sa ibinigay na 2K13ROSTER.ROS

Nabuksan ang file gamit ang David2KTool roster engine. Bersiyon 5 ito at lumang player rosters ang laman nito (hal. Ricky Rubio at Kevin Love sa Minnesota), kaya hindi nito kinakatawan ang modernong NBA roster. Ang fix na ito ay para sa source code at online ratings parser; hindi nito binabago o ini-edit ang original `.ROS` file.

## Validation

- `python3 -m compileall -q main.py cli.py nba2k20 tests` — pumasa.
- `python3 -m unittest discover -s tests` — **298 tests passed, 1 skipped**.
- Live Joel Embiid page HTML parser check — **27 fields**, OVR 91; sample values tumugma sa page.
