#!/usr/bin/env bash
fix_onlinefix_ini() {  # <dir>
    local dir="$1"
    local ini="$dir/OnlineFix.ini"
    [[ -f "$ini" ]] || return 0
    [[ -n "$FAKE_APPID$REAL_APPID" ]] || return 0

    local backup="$ini.bak"
    if (( ! DRY )); then
        [[ -f "$backup" ]] || cp "$ini" "$backup" || return 1
    fi

    local key value
    for key in FakeAppId RealAppId; do
        case "$key" in
            FakeAppId) value="$FAKE_APPID" ;;
            RealAppId) value="$REAL_APPID" ;;
        esac
        [[ -n "$value" ]] || continue
        if grep -q "^$key=" "$ini"; then
            if (( DRY )); then
                info "  OnlineFix.ini: $key=$value (seria alterado)"
            else
                sed -i "s/^$key=.*/$key=$value/" "$ini"
                ok "OnlineFix.ini: $key=$value"
            fi
        else
            if (( DRY )); then
                info "  OnlineFix.ini: $key=$value (seria adicionado)"
            else
                err "OnlineFix.ini não contém $key; alteração automática recusada para não gravar na seção errada"
                return 1
            fi
        fi
    done
}
