#!/bin/bash
set -e
BASE_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$BASE_DIR"
mkdir -p export

sizes=(512 192 128 96 64 48)
for s in "${sizes[@]}"; do
  rsvg-convert -w $s -h $s icon_eye.svg -o export/icon_${s}.png || echo "Install librsvg (brew install librsvg) for PNG export"
done
cp icon_eye.svg export/icon.svg
cp logo_falconeye.svg export/logo.svg
echo "Exported to $BASE_DIR/export"

