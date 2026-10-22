#!/usr/bin/env bash
REG_CACHE=""

reg_query() {  # <id> <chave reg.exe> -> linhas "nome=valor"
    local id="$1" key="$2" out
    out="$(proton_run_out "$id" reg.exe query "$key")" || return 1
    printf '%s\n' "$out" | awk '
        /^[[:space:]]*[^[:space:]]+[[:space:]]+REG_[A-Z_]+[[:space:]]+/ {
            line = $0; sub(/^[[:space:]]+/, "", line)
            name = line; sub(/[[:space:]].*$/, "", name)
            val  = line; sub(/^[^[:space:]]+[[:space:]]+REG_[A-Z_]+[[:space:]]+/, "", val)
            gsub(/^"|"$/, "", val); sub(/\r$/, "", val)
            print name "=" val
        }'
}

reg_healthy() {  # <id> -> a consulta ao registro funciona?
    local id="$1"
    STEAM_COMPAT_CLIENT_INSTALL_PATH="$(steam_root)" \
    STEAM_COMPAT_DATA_PATH="$(compat_dir)/$id" \
    STEAM_COMPAT_INSTALL_PATH="$(steam_root)" \
        "$PROTON/proton" runinprefix reg.exe query 'HKCU\Software\Wine' >/dev/null 2>&1
}

reg_load() {  # <id> <chave reg.exe> -> preenche REG_CACHE
    local id="$1" key="$2" i out
    for i in 1 2 3; do
        if out="$(reg_query "$id" "$key")"; then REG_CACHE="$out"; return 0; fi
        sleep 2
    done
    # falhou: a chave pode não existir ainda, ou o Proton pode estar com problema
    if reg_healthy "$id"; then REG_CACHE=""; return 0; fi
    REG_CACHE=""; return 1
}

reg_get() {  # <nome> -> valor (vazio se não existir). Sempre retorna 0.
    [[ -n "$REG_CACHE" ]] || return 0
    local v
    v="$(printf '%s\n' "$REG_CACHE" | grep -i "^$1=" | head -1 | cut -d= -f2- | tr -d '\r')" || v=""
    printf '%s' "$v"
    return 0
}

reg_set() {  # <id> <chave reg.exe> <nome> <valor>
    local id="$1" key="$2" name="$3" val="$4"
    local tmp src
    tmp="$(mktemp -d)"; src="$tmp/overrides.reg"
    {
        echo "REGEDIT4"
        echo
        echo "[${key/HKCU/HKEY_CURRENT_USER}]"
        printf '"%s"="%s"\n' "$name" "$val"
    } >"$src"
    proton_run "$id" reg.exe import "$(to_win_path "$src")"
    local rc=$?
    rm -rf "$tmp"
    return $rc
}

reg_del() {  # <id> <chave reg.exe> <nome>
    local id="$1" key="$2" name="$3"
    local tmp src
    tmp="$(mktemp -d)"; src="$tmp/overrides.reg"
    {
        echo "REGEDIT4"
        echo
        echo "[${key/HKCU/HKEY_CURRENT_USER}]"
        printf '"%s"=-\n' "$name"
    } >"$src"
    proton_run "$id" reg.exe import "$(to_win_path "$src")"
    local rc=$?
    rm -rf "$tmp"
    return $rc
}
