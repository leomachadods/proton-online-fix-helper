#!/usr/bin/env bash
# Configuração é dado, nunca código: não usar source/eval.
config_read() {
    local key="$1" path="${2:-$GAME_DIR}" section
    [[ -f "$CONFIG_FILE" ]] || return 1
    section="$(printf '%s' "$path" | tr '/' '_')"
    SECTION="[$section]" KEY="$key" awk '
        $0 == ENVIRON["SECTION"] { f=1; next }
        /^\[/ { f=0 }
        f && index($0, ENVIRON["KEY"] "=") == 1 {
            sub(/^[^=]*=/, ""); print; exit
        }
    ' "$CONFIG_FILE"
}

config_save() {
    local section tmp
    section="$(printf '%s' "$GAME_DIR" | tr '/' '_')"
    [[ "$GAME_DIR" != *$'\n'* && "$GAME_DIR" != *']'* ]] || return 1
    mkdir -p "$CONFIG_DIR" || return 1
    # Evita perder atualizações de outro processo; gravar no mesmo filesystem.
    local lock="$CONFIG_DIR/.save-lock"
    mkdir "$lock" 2>/dev/null || { err "outra gravação de configuração está em andamento"; return 1; }
    tmp="$(mktemp "$CONFIG_DIR/.games.XXXXXX")" || { rmdir "$lock"; return 1; }
    if [[ -f "$CONFIG_FILE" ]]; then
        SECTION="[$section]" awk '
            /^\[/ { skip=($0 == ENVIRON["SECTION"]) }
            !skip { print }
        ' "$CONFIG_FILE" >"$tmp" || { rm -f "$tmp"; rmdir "$lock"; return 1; }
    fi
    {
        printf '[%s]\npath=%s\n' "$section" "$GAME_DIR"
        [[ -z "$COMPAT_ID" ]] || printf 'compatdata=%s\n' "$COMPAT_ID"
        [[ -z "$APPID" ]] || printf 'appid=%s\n' "$APPID"
        [[ -z "$WANT_DLLS" ]] || printf 'dll=%s\n' "$WANT_DLLS"
        [[ -z "$FAKE_APPID" ]] || printf 'fake_appid=%s\n' "$FAKE_APPID"
        [[ -z "$REAL_APPID" ]] || printf 'real_appid=%s\n' "$REAL_APPID"
        printf '\n'
    } >>"$tmp"
    chmod 600 "$tmp"
    local rc=0
    mv "$tmp" "$CONFIG_FILE" || rc=$?
    rmdir "$lock"
    (( rc == 0 )) && ok "opções salvas em $CONFIG_FILE"
    return "$rc"
}
