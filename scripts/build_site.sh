#!/usr/bin/env bash
# Build the static dashboard into $1 (default: dist), stamped with environment label $2.
set -euo pipefail
OUT="${1:-dist}"
ENV_LABEL="${2:-development}"

rm -rf "$OUT"
mkdir -p "$OUT/data" "$OUT/snapshots"
cp -r site/. "$OUT/"
cp -r data/. "$OUT/data/"
cp -r snapshots/. "$OUT/snapshots/"
sed -i.bak "s/__ENV__/${ENV_LABEL}/g" "$OUT/index.html" && rm -f "$OUT/index.html.bak"

echo "built $OUT (env=${ENV_LABEL})"
