#!/usr/bin/env bash
#
# print-pdf.sh — always-prepend-blank-page wrapper for the EPSON WF7820.
#
# The EPSON_WF7820_Direct printer consistently drops the first page of an
# `lp` job. This wrapper prepends a blank sacrificial page so the real
# page 1 always reaches paper.
#
# Usage:
#   ./print-pdf.sh worksheet.pdf                     # two-sided long-edge (default)
#   ./print-pdf.sh --one-sided worksheet.pdf         # single-sided
#   ./print-pdf.sh --short-edge worksheet.pdf        # two-sided short-edge (tumble)
#   ./print-pdf.sh --printer NAME worksheet.pdf      # override printer
#   ./print-pdf.sh --copies 2 worksheet.pdf          # N copies
#
# Requires: pdfunite (from poppler-utils).

set -euo pipefail

PRINTER="${EPSON_PRINTER:-EPSON_WF7820_Direct}"
SIDES="two-sided-long-edge"
COPIES=1

while [[ $# -gt 0 ]]; do
    case "$1" in
        --one-sided)   SIDES="one-sided"; shift ;;
        --long-edge)   SIDES="two-sided-long-edge"; shift ;;
        --short-edge)  SIDES="two-sided-short-edge"; shift ;;
        --printer)     PRINTER="$2"; shift 2 ;;
        --copies)      COPIES="$2"; shift 2 ;;
        -h|--help)     sed -n '3,18p' "$0"; exit 0 ;;
        -*)            echo "Unknown flag: $1" >&2; exit 1 ;;
        *)             PDF="$1"; shift ;;
    esac
done

if [[ -z "${PDF:-}" ]]; then
    echo "Usage: $0 [--one-sided|--short-edge] [--printer NAME] [--copies N] <pdf>" >&2
    exit 1
fi

if [[ ! -f "$PDF" ]]; then
    echo "File not found: $PDF" >&2
    exit 1
fi

if ! command -v pdfunite >/dev/null 2>&1; then
    echo "pdfunite not installed — install poppler-utils (sudo apt install poppler-utils)" >&2
    exit 1
fi

# Minimal blank Letter-size PDF (612x792 pt). Stored alongside this script so
# it's generated once and reused.
BLANK="$(dirname "$(readlink -f "$0")")/.blank.pdf"
if [[ ! -f "$BLANK" ]]; then
    cat > "$BLANK" <<'BLANK_PDF'
%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000053 00000 n
0000000098 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
170
%%EOF
BLANK_PDF
fi

TMP="$(mktemp --suffix=.pdf)"
trap 'rm -f "$TMP"' EXIT

pdfunite "$BLANK" "$PDF" "$TMP"

LP_ARGS=(-d "$PRINTER" -o "sides=$SIDES" -n "$COPIES")
# Give each job a readable title based on the original filename
LP_ARGS+=(-t "$(basename "$PDF")")

echo "Printing: $(basename "$PDF") → $PRINTER (sides=$SIDES, copies=$COPIES)"
lp "${LP_ARGS[@]}" "$TMP"
