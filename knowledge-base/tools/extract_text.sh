#!/usr/bin/env bash
# Extract text from sources/*.pdf into text/*.txt (needs poppler-utils: pdftotext).
# Journal officiel texts are two-column: extracted in reading order (no -layout).
# Tables (tariff, rulings, reports) keep their columns with -layout.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p text
for f in sources/*.pdf; do
  b=$(basename "$f" .pdf)
  case "$b" in
    loi_*|decret_*) pdftotext "$f" "text/$b.txt" ;;
    *)              pdftotext -layout "$f" "text/$b.txt" ;;
  esac
  echo "text/$b.txt"
done
