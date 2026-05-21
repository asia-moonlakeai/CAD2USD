#!/usr/bin/env bash
# =============================================================================
#  CAD to USD Converter — Single File
#
#  Usage:
#    ./convert.sh  <input_file>  [output_file]  [options]
#
#  Options:
#    --fine           High quality tessellation (chord=0.001, angle=10°)
#    --coarse         Fast preview tessellation (chord=0.1, angle=45°)
#    --no-materials   Skip material/texture conversion
#    --single-mesh    Flatten assembly into one mesh
#    --usda           Output as .usda (human-readable ASCII)
#    --usdz           Output as .usdz (zip package, for AR/mobile)
#    --verbose        Verbose output
#    --formats        List all supported formats and exit
#
#  Examples:
#    ./convert.sh  wheel.prt
#    ./convert.sh  assembly.asm  /out/assembly.usd
#    ./convert.sh  part.stp  --fine  --no-materials
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

# --- Handle --formats or no args ---
if [[ $# -eq 0 || "${1:-}" == "--formats" ]]; then
    "$PYTHON_EXE" -c \
        "import sys; sys.path.insert(0,'$REPO'); from src.formats import print_format_table; print_format_table()"
    exit 0
fi

"$PYTHON_EXE" "$REPO/app/run_conversion.py" \
    --format "$DEFAULT_OUTPUT_FORMAT" \
    "$@"
