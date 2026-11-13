#!/data/data/com.termux/files/usr/bin/bash
# Usage: bash termux_build.sh [zip] [USER/REPO]
set -e
pkg install -y gh git unzip python >/dev/null 2>&1 || pkg install -y gh git unzip python
[ -d ~/storage/downloads ] || { termux-setup-storage; sleep 6; }

ZIP="${1:-$(ls -t ~/storage/downloads/nba2k20_android_tool*.zip 2>/dev/null | head -1)}"
[ -f "$ZIP" ] || { echo "Walang zip sa Downloads"; exit 1; }
echo "Zip: $ZIP"

# kailangan ang 'workflow' scope para makapag-push ng .github/workflows
gh auth status >/dev/null 2>&1 || gh auth login -h github.com -p https -w -s workflow
gh auth status 2>&1 | grep -q workflow || gh auth refresh -h github.com -s workflow
gh auth setup-git
USERNAME=$(gh api user -q .login)
REPO="${2:-$USERNAME/nba2k20-tool}"
echo "Repo: $REPO"

D=~/tool_build
rm -rf "$D"; mkdir -p "$D"
unzip -q "$ZIP" -d "$D"
cd "$D"
python3 -m compileall -q main.py cli.py nba2k20
[ -f nba2k20/roster_core.py ] || { echo "ERROR: kulang ang nba2k20/roster_core.py sa ZIP"; exit 1; }
python3 tests/test_roster.py || { echo "ERROR: bumagsak ang roster self-test"; exit 1; }
echo "OK: Python sources + pure-Python roster engine (walang Java)."
rm -rf __pycache__ nba2k20/__pycache__ termux_build*.sh

gh repo view "$REPO" >/dev/null 2>&1 || gh repo create "$REPO" --private
rm -rf .git
git init -q -b main
git add -A
git -c user.name="$USERNAME" -c user.email="$USERNAME@users.noreply.github.com" commit -q -m "build [skip ci]"
git remote add origin "https://github.com/$REPO.git"
git push -f origin main

sleep 4
PREV=$(gh run list -R "$REPO" -w build.yml -L 1 --json databaseId -q '.[0].databaseId' 2>/dev/null || true)
PREV=${PREV:-0}
gh workflow run build.yml -R "$REPO" -f variant=full

RUN=""
for i in $(seq 1 30); do
  sleep 4
  RUN=$(gh run list -R "$REPO" -w build.yml -L 1 --json databaseId -q '.[0].databaseId' 2>/dev/null || true)
  [ -n "$RUN" ] && [ "$RUN" != "$PREV" ] && break
  RUN=""
done
[ -n "$RUN" ] || { echo "Walang bagong run. Tingnan: https://github.com/$REPO/actions"; exit 1; }

echo "Build run: $RUN (20-40 min, huwag isara ang Termux)"
termux-wake-lock 2>/dev/null || true
gh run watch "$RUN" -R "$REPO" --exit-status || { echo "FAILED. Tingnan: https://github.com/$REPO/actions/runs/$RUN"; exit 1; }

OUT=~/storage/downloads/apk_build
rm -rf "$OUT"; mkdir -p "$OUT"
gh run download "$RUN" -R "$REPO" -D "$OUT"
APKS=$(find "$OUT" -name "*.apk")
[ -n "$APKS" ] || { echo "Walang APK sa artifacts."; exit 1; }
echo "TAPOS! APK nasa: Downloads/apk_build"
echo "$APKS"
