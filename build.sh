#!/bin/bash
# Build dist/ThaiW3Setup-<version>-macos-<arch>.zip
#   ./build.sh            download the latest translations, then build
#   ./build.sh offline    reuse assets/translations.json.gz
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || python3 -m venv .venv
PY=.venv/bin/python
"$PY" -m pip install --disable-pip-version-check -q -r requirements-build.txt

[ -f packaging/icon.icns ] || "$PY" devtools/make_icon.py

if [ "${1-}" = offline ]; then
    [ -f assets/translations.json.gz ] || {
        echo 'assets/translations.json.gz is missing, run without "offline" first' >&2
        exit 1
    }
else
    "$PY" -m core.sheet --export assets/translations.json.gz
fi

"$PY" -m PyInstaller --noconfirm --clean ThaiW3Setup.spec

VERSION=$("$PY" -c "import core; print(core.__version__)")
STAGE="dist/ThaiW3Setup-macos"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R dist/ThaiW3Setup.app "$STAGE/"
cp README.md "$STAGE/"
cp packaging/first-run-macos.txt "$STAGE/อ่านก่อนเปิดครั้งแรก.txt"

ZIP="dist/ThaiW3Setup-$VERSION-macos-$(uname -m).zip"
rm -f "$ZIP" "$ZIP.sha256"
# ditto, not zip: it keeps the symlinks and extended attributes the code signature is checked against
ditto -c -k --keepParent "$STAGE" "$ZIP"
HASH=$(shasum -a 256 "$ZIP" | cut -d' ' -f1)
echo "$HASH  $(basename "$ZIP")" > "$ZIP.sha256"

echo
echo "SHA256 $HASH"
echo "Built $ZIP"
