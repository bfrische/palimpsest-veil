#!/bin/bash
# Palimpsest Veil — one-click installer.
#
# Double-click this file in Finder. It will:
#   1. set up the Python engine (first run downloads ~1 GB of models),
#   2. install the Photoshop plugin (no signing / Creative Cloud needed),
#   3. install a background service so the engine starts itself at login.
#
# Nothing here needs a terminal afterwards. To remove it, run uninstall.command.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ENGINE="$HERE/engine"
PLUGIN="$HERE/plugin"

PLUGIN_ID="com.palimpsest.veil"
VERSION="$(python3 -c "import json;print(json.load(open('$PLUGIN/manifest.json'))['version'])")"
HOSTMIN="$(python3 -c "import json;print(json.load(open('$PLUGIN/manifest.json'))['host']['minVersion'])")"

UXP_EXTERNAL="$HOME/Library/Application Support/Adobe/UXP/Plugins/External"
UXP_INFO="$HOME/Library/Application Support/Adobe/UXP/PluginsInfo/v1/PS.json"
DEST="$UXP_EXTERNAL/${PLUGIN_ID}_${VERSION}"

LA_DIR="$HOME/Library/LaunchAgents"
LA_LABEL="com.palimpsest.veil"
LA_PLIST="$LA_DIR/${LA_LABEL}.plist"
SUPPORT="$HOME/Library/Application Support/PalimpsestVeil"
LOG="$SUPPORT/engine.log"

VENV="$ENGINE/.venv"
PY="$VENV/bin/python"

echo "======================================"
echo "  Palimpsest Veil — installer"
echo "======================================"
echo

# --- 1. Python engine ------------------------------------------------------
if [ -x "$PY" ] && "$PY" -c "import torch, fastapi, diffusers" 2>/dev/null; then
  echo "[1/4] Engine dependencies already installed."
else
  echo "[1/4] Setting up the Python engine (first time can take several minutes)…"
  python3 -m venv "$VENV"
  "$PY" -m pip install --quiet --upgrade pip
  "$PY" -m pip install --quiet -r "$ENGINE/requirements.txt"
fi

# --- 2. Install the plugin folder -----------------------------------------
echo "[2/4] Installing plugin -> $DEST"
mkdir -p "$UXP_EXTERNAL"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -R "$PLUGIN/manifest.json" "$PLUGIN/index.html" "$PLUGIN/src" "$PLUGIN/icons" "$DEST/"

# --- 3. Register with Photoshop (PS.json) ---------------------------------
echo "[3/4] Registering the plugin with Photoshop"
mkdir -p "$(dirname "$UXP_INFO")"
INFO="$UXP_INFO" PLUGIN_ID="$PLUGIN_ID" VERSION="$VERSION" HOSTMIN="$HOSTMIN" NAME="Palimpsest Veil" python3 <<'PY'
import json, os, shutil
info = os.environ["INFO"]; pid = os.environ["PLUGIN_ID"]; ver = os.environ["VERSION"]
entry = {
    "hostMinVersion": os.environ["HOSTMIN"],
    "name": os.environ["NAME"],
    "path": f"$localPlugins/External/{pid}_{ver}",
    "pluginId": pid,
    "status": "enabled",
    "type": "uxp",
    "versionString": ver,
}
data = {"plugins": []}
if os.path.exists(info):
    shutil.copy2(info, info + ".bak")          # backup before touching it
    try:
        data = json.load(open(info))
    except Exception:
        data = {"plugins": []}
data.setdefault("plugins", [])
# preserve every other plugin; replace only our own entry
data["plugins"] = [p for p in data["plugins"] if p.get("pluginId") != pid]
data["plugins"].append(entry)
json.dump(data, open(info, "w"), indent=4)
print(f"      registered {pid} {ver} (other plugins preserved: "
      f"{[p.get('pluginId') for p in data['plugins'] if p.get('pluginId') != pid]})")
PY

# --- 4. Background engine service -----------------------------------------
echo "[4/4] Installing the auto-start engine service"
mkdir -p "$LA_DIR" "$SUPPORT"
cat > "$LA_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LA_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PY}</string>
    <string>-m</string>
    <string>veil</string>
    <string>serve</string>
  </array>
  <key>WorkingDirectory</key><string>${ENGINE}</string>
  <key>EnvironmentVariables</key>
  <dict><key>HF_HUB_DISABLE_PROGRESS_BARS</key><string>1</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>${LOG}</string>
  <key>StandardErrorPath</key><string>${LOG}</string>
</dict>
</plist>
PLIST

UID_NUM="$(id -u)"
# Reloading a launch agent is idempotent but each step returns non-zero in the
# "already/never loaded" cases — never let that abort the installer.
set +e
launchctl bootout "gui/${UID_NUM}/${LA_LABEL}" 2>/dev/null
sleep 1
launchctl bootstrap "gui/${UID_NUM}" "$LA_PLIST" 2>/dev/null
launchctl enable "gui/${UID_NUM}/${LA_LABEL}" 2>/dev/null
launchctl kickstart -k "gui/${UID_NUM}/${LA_LABEL}" 2>/dev/null
set -e

printf "      waiting for the engine to answer"
for _ in $(seq 1 25); do
  if curl -fs "http://127.0.0.1:8760/health" >/dev/null 2>&1; then
    ENGINE_UP=1; break
  fi
  printf "."; sleep 1
done
echo

echo
echo "======================================"
if [ "${ENGINE_UP:-0}" = "1" ]; then
  echo "  Engine running: http://127.0.0.1:8760  ✔"
else
  echo "  Engine service installed. It may still be starting;"
  echo "  logs: $LOG"
fi
echo "  It now starts automatically every login."
echo
echo "  LAST STEP: quit and reopen Photoshop, then open"
echo "  Plugins  ▸  Palimpsest Veil"
echo "======================================"
echo
[ -t 0 ] && { read -n 1 -s -r -p "Press any key to close."; echo; }
