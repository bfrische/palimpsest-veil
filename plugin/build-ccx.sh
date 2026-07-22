#!/usr/bin/env bash
# Package the UXP plugin into a .ccx — a zip archive with manifest.json at its
# root, which is what Photoshop's plugin installer expects.
#
# Note: this produces an UNSIGNED .ccx, which loads fine via the UXP Developer
# Tool and installs on most setups. For a fully SIGNED distributable package,
# use the UXP Developer Tool's "Package" action instead.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="$HERE/dist"
NAME="palimpsest-veil"
VERSION="$(python3 -c "import json;print(json.load(open('$HERE/manifest.json'))['version'])")"
CCX="$OUT_DIR/${NAME}-${VERSION}.ccx"

mkdir -p "$OUT_DIR"
rm -f "$CCX"

cd "$HERE"
# manifest.json MUST be at the archive root — zip from inside the plugin dir.
zip -r -X "$CCX" manifest.json index.html icons src \
  -x '*.DS_Store' -x '__MACOSX*' >/dev/null

echo "Built $CCX"
echo "--- contents ---"
unzip -l "$CCX"
