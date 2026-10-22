#!/usr/bin/env bash
lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

contains() {  # contains <item> <lista separada por espaço>
    local needle="$1" item
    for item in $2; do [[ "$item" == "$needle" ]] && return 0; done
    return 1
}

steam_root() {
    if [[ -n "${STEAM_ROOT:-}" ]]; then printf '%s' "$STEAM_ROOT"; return 0; fi
    local c
    for c in \
        "$HOME/.local/share/Steam" \
        "$HOME/.steam/steam" \
        "$HOME/.steam/root" \
        "$HOME/Library/Application Support/Steam"
    do
        [[ -d "$c/steamapps" ]] && { printf '%s' "$c"; return 0; }
    done
    return 1
}

compat_dir() { printf '%s/steamapps/compatdata' "$(steam_root)"; }
common_dir() { printf '%s/steamapps/common' "$(steam_root)"; }

game_dir_of() {  # <appid> -> pasta do jogo
    local acf dir
    acf="$(steam_root)/steamapps/appmanifest_$1.acf"
    [[ -f "$acf" ]] || return 1
    dir="$(awk -F'"' '/"installdir"/{print $4; exit}' "$acf")"
    [[ -n "$dir" ]] || return 1
    printf '%s/%s' "$(common_dir)" "$dir"
}

find_proton() {  # <compatdata id>
    local id="$1" cfg root d
    cfg="$(compat_dir)/$id/config_info"
    if [[ -f "$cfg" ]]; then
        root="$(grep -m1 '/files/share/fonts/' "$cfg" 2>/dev/null | sed 's|/files/share/fonts/.*||')"
        [[ -n "$root" && -x "$root/proton" ]] && { printf '%s' "$root"; return 0; }
    fi
    if [[ -n "${PROTON_ROOT:-}" && -x "${PROTON_ROOT}/proton" ]]; then
        printf '%s' "$PROTON_ROOT"; return 0
    fi
    for d in "$(steam_root)"/compatibilitytools.d/*/ "$(common_dir)"/Proton*/; do
        [[ -x "${d}proton" ]] && { printf '%s' "${d%/}"; return 0; }
    done
    return 1
}

# Roda um programa dentro do prefixo. "runinprefix" executa direto (a saída
# aparece no terminal); Proton antigo também suporta esse verbo. O Proton falha
# esporadicamente (exit 126) quando o wineserver do prefixo sobe/desce, então
# há retry.
proton_run() {  # <compatdata id> <prog> [args...]
    local id="$1"; shift
    local i rc=1
    for i in 1 2 3; do
        STEAM_COMPAT_CLIENT_INSTALL_PATH="$(steam_root)" \
        STEAM_COMPAT_DATA_PATH="$(compat_dir)/$id" \
        STEAM_COMPAT_INSTALL_PATH="$(steam_root)" \
            "$PROTON/proton" runinprefix "$@" >/dev/null 2>&1 && return 0
        rc=$?
        sleep 2
    done
    return $rc
}

# Roda um programa no prefixo mostrando a saída (usado pelo reg.exe query).
proton_run_out() {  # <compatdata id> <prog> [args...]
    local id="$1"; shift
    STEAM_COMPAT_CLIENT_INSTALL_PATH="$(steam_root)" \
    STEAM_COMPAT_DATA_PATH="$(compat_dir)/$id" \
    STEAM_COMPAT_INSTALL_PATH="$(steam_root)" \
        "$PROTON/proton" runinprefix "$@" 2>/dev/null
}

# unix -> caminho Windows. No prefix Wine, Z: aponta para a raiz do filesystem.
to_win_path() {
    local p="${1#/}"
    printf 'Z:\\%s' "${p//\//\\}"
}
