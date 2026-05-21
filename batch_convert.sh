#!/usr/bin/env bash
# =============================================================================
#  CAD to USD Converter — Batch Folder Conversion
#
#  Recursively scans a folder for all supported CAD files and converts them
#  to USD, preserving the directory structure in the output folder.
#
#  Usage:
#    ./batch_convert.sh  <input_folder>  [output_folder]  [options]
#
#  Options:
#    --flat            Do not recurse into subfolders
#    --skip-existing   Skip files whose USD output already exists
#    --dry-run         Print what would be converted without doing it
#    --ext EXT         Only convert files with this extension (e.g. .prt)
#    --no-materials    Skip material/texture conversion
#    --single-mesh     Flatten all assemblies into one mesh
#    --fine            High quality tessellation
#    --coarse          Fast preview tessellation
#    --usda            Output as .usda (human-readable ASCII)
#    --usdz            Output as .usdz package
#    --verbose         Show detailed output per file
#    --formats         Print all supported input formats and exit
#
#  Examples:
#    ./batch_convert.sh  /cad/models  /usd/output
#    ./batch_convert.sh  /cad/models  /usd/output  --skip-existing --fine
#    ./batch_convert.sh  /cad/models  --ext .prt  --ext .asm
#    ./batch_convert.sh  /cad/models  --dry-run
# =============================================================================

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Load config.env ---
if [[ ! -f "$REPO/config.env" ]]; then
    echo ""
    echo " [ERROR] config.env not found. Run ./install.sh first."
    echo ""
    exit 1
fi

while IFS='=' read -r key value; do
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    export "$key"="$value"
done < "$REPO/config.env"

PYTHON_EXE="${PYTHON_EXE:-}"
if [[ -z "$PYTHON_EXE" || ! -x "$PYTHON_EXE" ]]; then
    echo " [ERROR] PYTHON_EXE not set or not found. Re-run ./install.sh."
    exit 1
fi

export OMNI_KIT_ACCEPT_EULA="${OMNI_KIT_ACCEPT_EULA:-yes}"
DEFAULT_OUTPUT_FORMAT="${DEFAULT_OUTPUT_FORMAT:-.usd}"
TESSELLATION_CHORD="${TESSELLATION_CHORD:-0.01}"
TESSELLATION_ANGLE="${TESSELLATION_ANGLE:-30}"

# --- Handle --formats or no args ---
if [[ $# -eq 0 || "${1:-}" == "--formats" ]]; then
    "$PYTHON_EXE" -c \
        "import sys; sys.path.insert(0,'$REPO'); from src.formats import print_format_table; print_format_table()"
    exit 0
fi

INPUT_DIR="$1"
shift

OUTPUT_DIR=""
if [[ $# -gt 0 && "${1:-}" != --* ]]; then
    OUTPUT_DIR="$1"
    shift
fi

echo ""
echo " ============================================================"
echo "  CAD to USD Converter — Batch Mode"
echo " ============================================================"
echo "  Input : $INPUT_DIR"
if [[ -n "$OUTPUT_DIR" ]]; then
    echo "  Output: $OUTPUT_DIR"
else
    echo "  Output: (next to each input file)"
fi
echo " ============================================================"
echo ""

"$PYTHON_EXE" "$REPO/run_batch.py" \
    --input "$INPUT_DIR" \
    --output "$OUTPUT_DIR" \
    --format "$DEFAULT_OUTPUT_FORMAT" \
    --tessellation-chord "$TESSELLATION_CHORD" \
    --tessellation-angle "$TESSELLATION_ANGLE" \
    "$@"
