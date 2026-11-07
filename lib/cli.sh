#!/usr/bin/env bash
COMMAND=""; GAME_DIR=""; APPID=""; COMPAT_ID=""; PROTON=""
WANT_DLLS=""; FAKE_APPID=""; REAL_APPID=""; TIMEOUT=45
DRY=0; FORCE=0; ALL_DLLS=0; SAVE=0; USE_CONFIG=1
NETSOCK_ACTION="status"; NETSOCK_PATCH=""; NETSOCK_USERDATA=""; NETSOCK_OPT=0
REG_KEY='HKCU\Software\Wine\DllOverrides'
declare -a EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        check|apply|remove|launch|list|netsock) COMMAND="$1" ;;
        -h|--help)        usage; exit 0 ;;
        -V|--version)     printf '%s %s\n' "$PROGNAME" "$VERSION"; exit 0 ;;
        --path)           GAME_DIR="${2:?--path precisa de um caminho}"; shift ;;
        --appid)          APPID="${2:?--appid precisa de um valor}"; shift ;;
        --compatdata)     COMPAT_ID="${2:?--compatdata precisa de um valor}"; shift ;;
        --dll)            WANT_DLLS="${2:?--dll precisa de uma lista}"; shift ;;
        --all-dlls)       ALL_DLLS=1 ;;
        --proton)         PROTON="${2:?--proton precisa de um caminho}"; shift ;;
        --steam-root)     STEAM_ROOT="${2:?--steam-root precisa de um caminho}"; shift ;;
        --patch)          NETSOCK_PATCH="${2:?--patch precisa de um caminho}"; NETSOCK_OPT=1; shift ;;
        --userdata)       NETSOCK_USERDATA="${2:?--userdata precisa de um caminho}"; NETSOCK_OPT=1; shift ;;
        --status)         NETSOCK_ACTION="status"; NETSOCK_OPT=1 ;;
        --apply)          NETSOCK_ACTION="apply"; NETSOCK_OPT=1 ;;
        --remove)         NETSOCK_ACTION="remove"; NETSOCK_OPT=1 ;;
        --fake-appid)     FAKE_APPID="${2:?--fake-appid precisa de um valor}"; shift ;;
        --real-appid)     REAL_APPID="${2:?--real-appid precisa de um valor}"; shift ;;
        --timeout)        TIMEOUT="${2:?--timeout precisa de um valor}"; shift ;;
        --dry-run)        DRY=1 ;;
        --force)          FORCE=1 ;;
        --save)           SAVE=1 ;;
        --no-config)      USE_CONFIG=0 ;;
        --)               shift; EXTRA_ARGS+=("$@"); break ;;
        -*)               die "opção desconhecida: $1 (use --help)" ;;
        *)                EXTRA_ARGS+=("$1") ;;
    esac
    shift
done

[[ -n "$COMMAND" ]] || { usage; die "informe um comando: check, apply, remove, launch, netsock ou list"; }
if (( NETSOCK_OPT )) && [[ "$COMMAND" != "netsock" ]]; then
    die "opções de netsock exigem o comando netsock"
fi
if [[ "$COMMAND" == "netsock" && -z "$APPID" ]]; then
    die "netsock requer --appid (o AppID do jogo na Steam)"
fi
[[ -z "$COMPAT_ID" || "$COMPAT_ID" =~ ^[0-9]+$ ]] || die "compatdata deve ser numérico"
[[ -z "$APPID" || "$APPID" =~ ^[0-9]+$ ]] || die "appid deve ser numérico"
[[ -z "$FAKE_APPID" || "$FAKE_APPID" =~ ^[0-9]+$ ]] || die "fake-appid deve ser numérico"
[[ -z "$REAL_APPID" || "$REAL_APPID" =~ ^[0-9]+$ ]] || die "real-appid deve ser numérico"
[[ "$TIMEOUT" =~ ^[1-9][0-9]*$ ]] || die "timeout inválido"
if [[ -n "$WANT_DLLS" ]]; then
    [[ "$WANT_DLLS" =~ ^[a-zA-Z0-9_-]+(,[a-zA-Z0-9_-]+)*$ ]] || die "lista de DLLs inválida (nomes sem extensão)"
fi

command -v awk >/dev/null || die "awk não encontrado"
command -v mktemp >/dev/null || die "mktemp não encontrado"

if [[ "$COMMAND" == "list" ]]; then
    steam_root >/dev/null || die "não achei o Steam (use --steam-root)"
    cmd_list
    exit 0
fi

if [[ "$COMMAND" == "netsock" ]]; then
    steam_root >/dev/null || die "não achei o Steam (use --steam-root)"
    command -v python3 >/dev/null || die "netsock requer Python 3.9+"
    ns_args=( "$NETSOCK_ACTION" --steam-root "$(steam_root)" --appid "$APPID" )
    [[ -n "$NETSOCK_PATCH" ]] && ns_args+=( --patch "$NETSOCK_PATCH" )
    [[ -n "$NETSOCK_USERDATA" ]] && ns_args+=( --userdata "$NETSOCK_USERDATA" )
    (( DRY )) && ns_args+=( --dry-run )
    (( FORCE )) && ns_args+=( --force )
    PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}" \
        python3 -m steamfix.netsock "${ns_args[@]}"
    exit $?
fi

# --- --path pode ser a pasta do jogo ou o próprio executável ---
if [[ -n "$GAME_DIR" && -f "$GAME_DIR" ]]; then
    GAME_DIR="$(dirname "$GAME_DIR")"
fi

# --- resolver o que ainda falta a partir do appid ---
if [[ -n "$APPID" && -z "$GAME_DIR" ]]; then
    GAME_DIR="$(game_dir_of "$APPID")" || die "jogo $APPID não instalado (sem appmanifest)"
fi
if [[ -n "$APPID" && -z "$COMPAT_ID" ]]; then
    COMPAT_ID="$APPID"
fi

# --- carregar do arquivo de config salvo ---
if (( USE_CONFIG )) && [[ -n "$GAME_DIR" ]]; then
    GAME_DIR="$(cd "$GAME_DIR" 2>/dev/null && pwd)" || die "pasta inexistente"
    [[ -n "$COMPAT_ID" ]]  || COMPAT_ID="$(config_read compatdata || true)"
    [[ -n "$APPID" ]]      || APPID="$(config_read appid || true)"
    [[ -n "$WANT_DLLS" ]]  || WANT_DLLS="$(config_read dll || true)"
    [[ -n "$FAKE_APPID" ]] || FAKE_APPID="$(config_read fake_appid || true)"
    [[ -n "$REAL_APPID" ]] || REAL_APPID="$(config_read real_appid || true)"
fi

[[ -n "$GAME_DIR" ]] || die "informe --path (pasta do jogo ou executável) ou --appid"
GAME_DIR="$(cd "$GAME_DIR" 2>/dev/null && pwd)" || die "pasta inexistente"

# --- descobrir o prefixo: config salvo -> atalho do Steam -> menu ---
if [[ -z "$COMPAT_ID" ]]; then
    COMPAT_ID="$(match_shortcut "$GAME_DIR")" || COMPAT_ID=""
    if [[ -n "$COMPAT_ID" ]]; then
        ok "prefixo detectado pelo atalho do Steam: $COMPAT_ID"
    else
        list_prefixes
        echo
        if [[ -t 0 ]]; then
            printf 'Escolha o prefixo (número) ou Enter para abortar: '
            read -r choice
            [[ -n "$choice" ]] || die "nenhum prefixo escolhido"
            [[ "$choice" =~ ^[1-9][0-9]*$ && "$choice" -le "${#PREFIX_IDS[@]}" ]] || die "escolha inválida: $choice"
            COMPAT_ID="${PREFIX_IDS[$((choice - 1))]:-}"
            [[ -n "$COMPAT_ID" ]] || die "escolha inválida: $choice"
            ok "prefixo escolhido: $COMPAT_ID"
        else
            die "não consegui casar a pasta com um prefixo; use --compatdata <id> (veja a lista acima)"
        fi
    fi
fi

steam_root >/dev/null || die "não achei o Steam (use --steam-root)"

if [[ -z "$PROTON" ]]; then
    PROTON="$(find_proton "$COMPAT_ID")" || die "nenhum Proton encontrado (use --proton)"
fi
[[ -x "$PROTON/proton" ]] || die "Proton inválido: $PROTON"

# Configuração salva também é entrada não confiável: validar após carregá-la.
[[ "$COMPAT_ID" =~ ^[0-9]+$ ]] || die "compatdata salvo inválido"
[[ -z "$FAKE_APPID" || "$FAKE_APPID" =~ ^[0-9]+$ ]] || die "fake-appid salvo inválido"
[[ -z "$REAL_APPID" || "$REAL_APPID" =~ ^[0-9]+$ ]] || die "real-appid salvo inválido"
[[ -z "$WANT_DLLS" || "$WANT_DLLS" =~ ^[a-zA-Z0-9_-]+(,[a-zA-Z0-9_-]+)*$ ]] || die "DLLs salvas inválidas"

RESULT=0
if [[ "$COMMAND" == "check" ]]; then
    cmd_check
elif [[ "$COMMAND" == "apply" ]]; then
    cmd_apply
elif [[ "$COMMAND" == "remove" ]]; then
    cmd_remove
elif [[ "$COMMAND" == "launch" ]]; then
    cmd_launch "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
fi
RESULT=$?

if (( SAVE && RESULT == 0 && ! DRY )); then
    [[ "$COMMAND" == "apply" || "$COMMAND" == "launch" ]] || die "--save só vale para apply/launch"
    config_save
fi
exit "$RESULT"
