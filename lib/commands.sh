#!/usr/bin/env bash
cmd_check() {
    local -a dlls=() stacks=()
    mapfile -t dlls < <(pick_dlls "$GAME_DIR")
    mapfile -t stacks < <(detect_stacks "$GAME_DIR")

    info "${C_BOLD}Pasta:${C_RESET}    $GAME_DIR"
    info "${C_BOLD}Prefixo:${C_RESET}  $(compat_dir)/$COMPAT_ID"
    info "${C_BOLD}Proton:${C_RESET}   $PROTON"
    info "${C_BOLD}Stack:${C_RESET}    ${stacks[*]:-nenhuma}"
    info "${C_BOLD}DLLs:${C_RESET}     ${dlls[*]:-nenhuma}"

    if [[ -f "$GAME_DIR/OnlineFix.ini" ]]; then
        info "${C_BOLD}OnlineFix.ini:${C_RESET}"
        sed 's/^/    /' "$GAME_DIR/OnlineFix.ini" | head -8
    fi

    if [[ -d "$(compat_dir)/$COMPAT_ID" ]]; then
        reg_load "$COMPAT_ID" "$REG_KEY" || { err "não consegui ler o registro"; return 1; }
        info "${C_BOLD}Overrides no prefixo:${C_RESET}"
        local d value
        for d in "${dlls[@]}"; do
            value="$(reg_get "$d")"
            if [[ "$value" == "n,b" ]]; then
                printf '    %s%s%s = n,b\n' "$C_GREEN" "$d" "$C_RESET"
            else
                printf '    %s%s%s = %s\n' "$C_RED" "$d" "$C_RESET" "${value:-<ausente>}"
            fi
        done
    else
        warn "prefixo $(compat_dir)/$COMPAT_ID ainda não existe (rode o jogo uma vez pelo Steam)"
    fi
}

cmd_apply() {
    local -a dlls=() todo=() already=()
    mapfile -t dlls < <(pick_dlls "$GAME_DIR")
    [[ ${#dlls[@]} -eq 0 ]] && { info "nenhuma DLL de sideload relevante na pasta."; return 0; }

    fix_onlinefix_ini "$GAME_DIR" || return 1

    if (( DRY )); then
        local proposed
        for proposed in "${dlls[@]}"; do
            info "Override proposto: $proposed=n,b (sem executar Proton)"
        done
        return 0
    fi

    if [[ ! -d "$(compat_dir)/$COMPAT_ID" ]]; then
        die "prefixo $(compat_dir)/$COMPAT_ID não existe (rode o jogo uma vez pelo Steam)"
    fi
    reg_load "$COMPAT_ID" "$REG_KEY" || { err "não consegui ler o registro do prefixo"; return 1; }

    local d value
    for d in "${dlls[@]}"; do
        value="$(reg_get "$d")"
        if [[ "$value" == "n,b" ]]; then
            already+=("$d")
        elif contains "$d" "$UNSAFE_CORE" && (( ! FORCE )); then
            warn "$d é DLL de núcleo do Windows — não aplicada (use --force)"
        else
            todo+=("$d")
        fi
    done
    (( ${#already[@]} )) && ok "já aplicado: ${already[*]}"

    if (( DRY )); then
        for d in "${todo[@]}"; do info "  $d SERIA APLICADO: $REG_KEY -> \"$d\"=\"n,b\""; done
        return 0
    fi
    [[ ${#todo[@]} -eq 0 ]] && return 0
    step "aplicando em $REG_KEY"
    apply_dlls "$COMPAT_ID" "$REG_KEY" apply "${todo[@]}"
}

cmd_remove() {
    local -a dlls=() rm=()
    mapfile -t dlls < <(pick_dlls "$GAME_DIR")
    [[ ${#dlls[@]} -eq 0 ]] && { info "nada a remover"; return 0; }
    [[ -d "$(compat_dir)/$COMPAT_ID" ]] || { info "prefixo inexistente"; return 0; }
    reg_load "$COMPAT_ID" "$REG_KEY" || return 1
    local d
    for d in "${dlls[@]}"; do
        [[ -n "$(reg_get "$d")" ]] && rm+=("$d")
    done
    [[ ${#rm[@]} -eq 0 ]] && { info "nada a remover"; return 0; }
    step "removendo overrides"
    if (( DRY )); then
        for d in "${rm[@]}"; do info "  $d SERIA REMOVIDO"; done
        return 0
    fi
    apply_dlls "$COMPAT_ID" "$REG_KEY" remove "${rm[@]}"
}

cmd_launch() {
    if (( DRY )); then
        info "Pré-visualização: nenhum jogo será aberto e nenhum prefixo será alterado."
        return 0
    fi
    local -a dlls=()
    mapfile -t dlls < <(pick_dlls "$GAME_DIR")
    if [[ ${#dlls[@]} -gt 0 ]]; then
        cmd_apply || return 1
    fi
    launch_game "$COMPAT_ID" "$GAME_DIR" "$@"
}

cmd_list() {
    list_prefixes
    echo
    info "Jogos com DLLs candidatas:"
    local acf a d
    local -a c
    for acf in "$(steam_root)"/steamapps/appmanifest_*.acf; do
        [[ -f "$acf" ]] || continue
        a="$(awk -F'"' '/"appid"/{print $4; exit}' "$acf")"
        d="$(game_dir_of "$a" 2>/dev/null)" || continue
        [[ -d "$d" ]] || continue
        mapfile -t c < <(candidates "$d")
        [[ ${#c[@]} -eq 0 ]] && continue
        printf '  %-10s %-42s %s\n' "$a" "$(basename "$d")" "${c[*]}"
    done
}
