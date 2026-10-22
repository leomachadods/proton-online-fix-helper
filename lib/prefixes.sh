#!/usr/bin/env bash
steam_shortcuts() {  # -> "appid|exe|startdir|nome" por linha
    command -v python3 >/dev/null 2>&1 || return 0
    python3 - <<'PY' 2>/dev/null || return 0
import re, struct, glob, os
for path in glob.glob(os.path.expanduser("~/.local/share/Steam/userdata/*/config/shortcuts.vdf")):
    try:
        data = open(path, "rb").read()
    except OSError:
        continue
    for m in re.finditer(rb"\x02appid\x00", data):
        i = m.end()
        appid = struct.unpack_from("<I", data, i)[0]
        rest = data[i + 4:]
        def grab(tag):
            mm = re.search(rb"\x01" + tag + rb"\x00", rest)
            if not mm:
                return ""
            j = mm.end()
            k = rest.find(b"\x00", j)
            return rest[j:k].decode("utf-8", "replace").strip('"')
        exe = grab(b"Exe")
        sd = grab(b"StartDir")
        name = grab(b"AppName") or grab(b"appname")
        print("%d|%s|%s|%s" % (appid, exe, sd, name))
PY
}

# Casa a pasta do jogo com o atalho do Steam -> id do prefixo
match_shortcut() {  # <dir do jogo> -> id do compatdata
    local dir="$1" line id exe sd
    while IFS='|' read -r id exe sd _; do
        [[ -n "$id" ]] || continue
        exe="${exe//\\/\/}"; sd="${sd//\\/\/}"
        if [[ -n "$exe" && "$(dirname "$exe")" == "$dir" ]]; then printf '%s' "$id"; return 0; fi
        if [[ -n "$sd" && "${sd%/}" == "$dir" ]]; then printf '%s' "$id"; return 0; fi
    done < <(steam_shortcuts)
    return 1
}

# Lista os prefixos Proton disponíveis, com um resumo de cada um.
# Deixa os ids em PREFIX_IDS (na mesma ordem em que foram impressos).
PREFIX_IDS=()

list_prefixes() {
    local dir id has_pfx proton name last n=0
    PREFIX_IDS=()
    printf '%s\n' "${C_BOLD}Prefixos Proton disponíveis:${C_RESET}"
    for dir in "$(compat_dir)"/*/; do
        [[ -d "$dir" ]] || continue
        id="$(basename "$dir")"
        has_pfx="sem prefix"
        [[ -d "$dir/pfx" ]] && has_pfx="com prefix"
        proton="$(proton_of_prefix "$id")"
        proton="$(basename "${proton:-sem info}")"
        name=""
        while IFS='|' read -r _aid _exe _sd nm; do
            [[ "$_aid" == "$id" ]] && { name="$nm"; break; }
        done < <(steam_shortcuts)
        if [[ -z "$name" && -f "$(steam_root)/steamapps/appmanifest_$id.acf" ]]; then
            name="$(awk -F'"' '/"name"/{print $4; exit}' "$(steam_root)/steamapps/appmanifest_$id.acf")"
        fi
        last="$(stat -c%y "$dir" 2>/dev/null | cut -d. -f1)"
        n=$((n + 1))
        PREFIX_IDS+=("$id")
        printf '  %2d) %-12s %-9s %-26s %-38s %s\n' "$n" "$id" "$has_pfx" "$proton" "${name:-—}" "${last:-—}"
    done
}

proton_of_prefix() {  # <id> -> caminho do Proton (ou vazio)
    local cfg root
    cfg="$(compat_dir)/$1/config_info"
    [[ -f "$cfg" ]] || return 1
    root="$(grep -m1 '/files/share/fonts/' "$cfg" 2>/dev/null | sed 's|/files/share/fonts/.*||')"
    [[ -n "$root" ]] && { printf '%s' "$root"; return 0; }
    return 1
}
