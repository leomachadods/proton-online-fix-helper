#!/usr/bin/env bash
# CLI compatível com as versões anteriores. Mantenha lib/ junto deste arquivo.
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for module in core steam registry dlls prefixes ini config runtime commands; do
    source "$SCRIPT_DIR/lib/$module.sh" || exit 1
done
source "$SCRIPT_DIR/lib/cli.sh"
