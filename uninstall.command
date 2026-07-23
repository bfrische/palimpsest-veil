#!/bin/bash
# Palimpsest Veil — uninstaller. Double-click to remove the plugin and the
# background engine service. (Leaves the Python venv and downloaded models in
# place; delete the project folder and ~/.cache/palimpsest-veil to remove those.)
set -uo pipefail

PLUGIN_ID="com.palimpsest.veil"
LA_LABEL="com.palimpsest.veil"
LA_PLIST="$HOME/Library/LaunchAgents/${LA_LABEL}.plist"
UXP_EXTERNAL="$HOME/Library/Application Support/Adobe/UXP/Plugins/External"
UXP_INFO="$HOME/Library/Application Support/Adobe/UXP/PluginsInfo/v1/PS.json"

echo "Removing Palimpsest Veil…"

# stop + remove the service
launchctl bootout "gui/$(id -u)/${LA_LABEL}" 2>/dev/null || launchctl unload "$LA_PLIST" 2>/dev/null || true
rm -f "$LA_PLIST"

# remove installed plugin folder(s)
rm -rf "$UXP_EXTERNAL/${PLUGIN_ID}"_* 2>/dev/null || true

# de-register from PS.json (keeps every other plugin)
if [ -f "$UXP_INFO" ]; then
  INFO="$UXP_INFO" PLUGIN_ID="$PLUGIN_ID" python3 <<'PY'
import json, os, shutil
info = os.environ["INFO"]; pid = os.environ["PLUGIN_ID"]
try:
    data = json.load(open(info))
except Exception:
    data = {"plugins": []}
shutil.copy2(info, info + ".bak")
data["plugins"] = [p for p in data.get("plugins", []) if p.get("pluginId") != pid]
json.dump(data, open(info, "w"), indent=4)
print("de-registered", pid)
PY
fi

echo "Done. Restart Photoshop to finish removing the panel."
[ -t 0 ] && { read -n 1 -s -r -p "Press any key to close."; echo; }
