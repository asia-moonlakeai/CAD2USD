#!/usr/bin/env bash
# =============================================================================
#  CAD to USD Converter — Environment Validator
#
#  Re-run environment checks without reinstalling.
#  Usage: ./validate.sh
# =============================================================================

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

"$PYTHON_EXE" "$REPO/setup/validate_env.py"
