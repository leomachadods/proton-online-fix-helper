#!/usr/bin/env bash
set -euo pipefail
[[ $(uname -s) == Linux ]] || { echo 'Requer Linux e Proton.' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'Instale Python 3.9+.' >&2; exit 1; }
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$ROOT/menu.py" "$@"
