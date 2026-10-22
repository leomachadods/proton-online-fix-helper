#!/usr/bin/env bash
netsock_path() {
    [[ "$NO_NETSOCK" -eq 1 ]] && return 1
    if [[ -n "$NETSOCK" ]]; then
        [[ -f "$NETSOCK" ]] && { printf '%s' "$NETSOCK"; return 0; }
        return 1
    fi
    local p
    for p in "$HOME/.config/SLSsteam/tools/netsock/netsock.so" \
             "$HOME/.local/share/SLSsteam/tools/netsock/netsock.so" \
             "$HOME/.config/steam-dll-fix/netsock.so"; do
        [[ -f "$p" ]] && { printf '%s' "$p"; return 0; }
    done
    return 1
}
