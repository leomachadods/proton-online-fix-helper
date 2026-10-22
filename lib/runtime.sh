#!/usr/bin/env bash
apply_dlls() {  # <id> <chave> <ação> <dll...>
    local id="$1" key="$2" action="$3"; shift 3
    local -a names=("$@")
    [[ ${#names[@]} -eq 0 ]] && return 0
    local n
    for n in "${names[@]}"; do
        if [[ "$action" == "remove" ]]; then
            reg_del "$id" "$key" "$n" || { err "falha ao remover $n"; return 1; }
        else
            reg_set "$id" "$key" "$n" "n,b" || { err "falha ao aplicar $n"; return 1; }
        fi
    done
    reg_load "$id" "$key" || return 1
    local failed=0
    for n in "${names[@]}"; do
        if [[ "$action" == "remove" ]]; then
            if [[ -z "$(reg_get "$n")" ]]; then ok "$n removido"; else err "$n ainda presente"; failed=1; fi
        else
            if [[ "$(reg_get "$n")" == "n,b" ]]; then ok "$n aplicado"; else err "$n não aplicou"; failed=1; fi
        fi
    done
    return "$failed"
}

verify_game() {  # <id> <dir> <dll...>
    local id="$1" dir="$2"; shift 2
    local -a dlls=("$@")
    local exe log tmp d line h
    local -a hits=()

    exe="$(main_exe "$dir")"
    [[ -n "$exe" ]] || { err "não encontrei um .exe para rodar"; return 1; }

    step "verificando (rodando $(basename "$exe") por ${TIMEOUT}s)"
    tmp="$(mktemp -d)"; log="$tmp/loaddll.log"

    ( cd "$dir" && STEAM_COMPAT_CLIENT_INSTALL_PATH="$(steam_root)" \
        STEAM_COMPAT_DATA_PATH="$(compat_dir)/$id" \
        STEAM_COMPAT_INSTALL_PATH="$(steam_root)" \
        WINEDEBUG=+loaddll \
        timeout "$TIMEOUT" "$PROTON/proton" run "$exe" ) >"$log" 2>&1 || true

    # o timeout mata o proton, mas o jogo continua vivo: fecha ele.
    # o padrão "Z:" só aparece na linha de comando dos processos wine.
    pkill -f -i "Z:.*$(basename "$exe")" >/dev/null 2>&1 || true
    sleep 1

    local found=0
    for d in "${dlls[@]}"; do
        hits=()
        mapfile -t hits < <(grep -iE "[\\\\/]${d}\.dll\" at .*: (native|builtin)" "$log" || true)
        line=""
        for h in "${hits[@]}"; do
            [[ "$h" == *": native"* ]] && { line="$h"; break; }
            [[ -z "$line" ]] && line="$h"
        done
        if [[ "$line" == *": native"* ]]; then
            ok "$d carregada como NATIVE (sideload ativo)"
            found=1
        elif [[ "$line" == *": builtin"* ]]; then
            err "$d ainda caindo no builtin do Wine (o override não pegou)"
        else
            warn "$d não apareceu no log de carga"
        fi
    done
    (( found )) || warn "nenhuma DLL foi carregada como native"
    info "  log completo: $log"
}

launch_game() {  # <id> <dir> [args...]
    local id="$1" dir="$2"; shift 2
    local exe; exe="$(main_exe "$dir")"
    [[ -n "$exe" ]] || { err "não encontrei um .exe para rodar"; return 1; }
    step "abrindo $(basename "$exe")"

    local net; net="$(netsock_path || true)"
    if [[ -n "$net" ]]; then
        info "  ${C_CYAN}patch de cert aplicado (LD_AUDIT):${C_RESET} $net"
    fi

    local -a envs=(
        "STEAM_COMPAT_CLIENT_INSTALL_PATH=$(steam_root)"
        "STEAM_COMPAT_DATA_PATH=$(compat_dir)/$id"
        "STEAM_COMPAT_INSTALL_PATH=$(steam_root)"
    )
    [[ -n "$net" ]] && envs+=("LD_AUDIT=$net")

    ( cd "$dir" && env "${envs[@]}" "$PROTON/proton" run "$exe" "$@" )
}
