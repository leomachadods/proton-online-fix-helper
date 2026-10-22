#!/usr/bin/env bash
candidates() {  # <dir> -> DLLs da pasta que o Wine ignoraria
    local dir="$1" f n
    for f in "$dir"/*.dll; do
        [[ -f "$f" ]] || continue
        n="$(lower "$(basename "$f" .dll)")"
        contains "$n" "$WINE_HARDCODED" && printf '%s\n' "$n"
    done
    return 0
}

detect_stacks() {  # <dir> -> "marcador:dll" por linha
    local dir="$1" entry dll marker
    for entry in $CONFLICT_PAIRS; do
        dll="${entry%%|*}"; marker="${entry##*|}"
        [[ -f "$dir/$dll" && -f "$dir/$marker" ]] && printf '%s:%s\n' "$marker" "$dll"
    done
    return 0
}

pick_dlls() {  # <dir> -> lista final de DLLs
    local dir="$1" d
    if [[ -n "$WANT_DLLS" ]]; then
        for d in ${WANT_DLLS//,/ }; do printf '%s\n' "$(lower "$d")"; done
        return 0
    fi
    if (( ALL_DLLS )); then candidates "$dir"; return 0; fi

    local -a stacks=()
    mapfile -t stacks < <(detect_stacks "$dir")
    if [[ ${#stacks[@]} -gt 1 ]]; then
        warn "mais de um sideload presente na pasta do jogo:" >&2
        local s
        for s in "${stacks[@]}"; do warn "  ${s%%:*} (usa ${s##*:})" >&2; done
        warn "eles conflitam entre si; usando só o primeiro (use --all-dlls para forçar)" >&2
    fi
    if [[ ${#stacks[@]} -gt 0 ]]; then
        printf '%s\n' "${stacks[0]##*:}" | sed 's/\.dll$//'
        return 0
    fi
    candidates "$dir"
    return 0
}

main_exe() {  # <dir> -> executável principal do jogo
    local dir="$1" f base best="" bestsz=0 sz
    local prefer; prefer="$(lower "$(basename "$dir")").exe"
    for f in "$dir"/*.exe; do
        [[ -f "$f" ]] || continue
        base="$(lower "$(basename "$f")")"
        case "$base" in
            unitycrashhandler*|crashpad*|unityshadercompiler*|unityplayer*|vcredist*) continue ;;
        esac
        [[ "$base" == "$prefer" ]] && { printf '%s' "$f"; return 0; }
        sz="$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null || echo 0)"
        if [[ "$sz" -gt "$bestsz" ]]; then bestsz="$sz"; best="$f"; fi
    done
    printf '%s' "$best"
}
