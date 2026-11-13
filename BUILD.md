# Build ng Kivy Android APK gamit ang Termux (walang AIDE)

Ang Termux script ay nagpa-preflight ng source ZIP, nagpu-push ng project sa GitHub, nagpapatakbo ng GitHub Actions/Buildozer build, at nagda-download ng APK. Hindi ito AIDE at hindi ito nagko-compile ng Android APK diretso sa Termux shell.

## Isang command flow

1. I-download ang latest fixed source ZIP sa `Download/`.
2. I-install ang Termux packages at mag-authenticate sa GitHub:

```sh
pkg install gh git unzip python -y
gh auth login -h github.com -p https -w -s workflow
termux-setup-storage
```

3. Kunin ang build script mula sa ZIP at patakbuhin ito:

```sh
unzip -p ~/storage/downloads/nba2k20_android_tool_v76_roster_fixed.zip termux_build.sh > ~/b.sh
bash ~/b.sh ~/storage/downloads/nba2k20_android_tool_v76_roster_fixed.zip
```

Opsyonal, ipasa ang GitHub repo bilang pangalawang argument:

```sh
bash ~/b.sh ~/storage/downloads/nba2k20_android_tool_v76_roster_fixed.zip USER/REPO
```

Kailangan ng GitHub account/token na may `workflow` permission. Huwag isara ang Termux habang tumatakbo ang workflow. Kapag matagumpay, ida-download ng script ang APK sa `Download/apk_build/`.

## I-check bago mag-install

- Dapat matapos nang successful ang GitHub Actions run.
- May bagong preflight ang Termux script para huminto kung luma/kulang ang ZIP.
- Roster Editor ay purong Python (`nba2k20/roster_core.py`): walang Java at walang pyjnius na kailangan para dito. May roster self-test ang workflow bago mag-build.

## Manual GitHub Actions build

1. I-upload/push ang buong source tree sa repo kasama ang `.github/workflows/build.yml`.
2. Sa GitHub, buksan ang **Actions → Build APK → Run workflow**, piliin ang `full` o `decode`.
3. I-download at i-install lamang ang APK kung pumasa ang `Check roster engine (pure Python)` step.

Kung pumalya ang build, ipadala ang log ng failed workflow (lalo na ang `Build APK` at `Check roster engine` steps). Huwag ipadala ang game roster file kung hindi kailangan sa build error.

## Fixed signing key = stable Device ID (license login)

Ang license login ay nagpapadala ng **Device ID** (Android ID) sa panel. Ang Android ID ay *nakatali sa signing key ng APK*,
at ang GitHub Actions ay gumagawa ng BAGONG debug key kada build, kaya **kada build ay iba ang Device ID** (kita mo sa login
screen) at ang panel ay tinatanggihan ang key ("Incorrect Key") dahil iba na ang device.

Isang beses lang ito (Termux: `pkg install openjdk-17`):

```
keytool -genkeypair -keystore debug.keystore -storepass android -keypass android -alias androiddebugkey \
        -keyalg RSA -keysize 2048 -validity 36500 -dname "CN=Android Debug,O=Android,C=US"
base64 -w0 debug.keystore
```

Ilagay ang buong output ng `base64` sa GitHub repo > Settings > Secrets and variables > Actions > **New repository secret**,
pangalan: `DEBUG_KEYSTORE_B64`. Itago ang `debug.keystore` (backup). Pagkatapos, lahat ng susunod na build ay pareho ang
signing key => pareho ang Device ID, at puwede nang i-update ang APK nang hindi ina-uninstall. Sa unang build na may fixed key
magbabago pa ng isang beses ang Device ID: i-reset ang device ng key sa panel (o gumawa ng bagong key).
