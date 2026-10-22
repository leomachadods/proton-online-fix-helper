#!/usr/bin/env bash
VERSION="1.1.0"
PROGNAME="${0##*/}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/steam-dll-fix"
CONFIG_FILE="$CONFIG_DIR/games.conf"

# --------------------------------------------------------------------- config --

# DLLs que o Wine resolve SEMPRE de system32 (hardcoded default load order).
WINE_HARDCODED="advapi32 bcrypt cabinet cfgmgr32 combase comctl32 coml2 \
crypt32 cryptbase dnsapi dwmapi gdi32 hid imagehlp imm32 iphlpapi jsproxy \
kerberos kernel32 kernelbase mpr msi mspatcha msvcrt mswsock netapi32 \
netutils nsi odbccp32 ole32 oleacc oleaut32 opengl32 psapi rpcrt4 sechost \
secur32 setupapi shcore shell32 shlwapi sxs tzres uiautomationcore urlmon \
user32 version win32u winhttp wininet winmm wintrust ws2_32"

# Núcleo do Windows: nunca aplicar sozinho (quebraria o prefix inteiro).
UNSAFE_CORE="advapi32 combase coml2 gdi32 kernel32 kernelbase msvcrt ole32 \
oleaut32 rpcrt4 sechost shell32 user32"

# Stacks de sideload que se machucam entre si: os dois fazem hook no mesmo
# SteamAPI e, juntos, travam o jogo com "Unsupported SteamUtils version!".
# Formato: "<dll>|<arquivo que marca a stack>".
CONFLICT_PAIRS="version.dll|netromancy.ini winmm.dll|OnlineFix.ini"

# -------------------------------------------------------------------- estilo --

if [[ -t 1 ]]; then
    C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'
    C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_CYAN=$'\033[36m'
else
    C_RESET=""; C_BOLD=""; C_RED=""; C_GREEN=""; C_YELLOW=""; C_CYAN=""
fi

info() { printf '%s\n' "$*"; }
step() { printf '%s==>%s %s\n' "$C_CYAN" "$C_RESET" "$*"; }
ok()   { printf '  %sok%s   %s\n' "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '  %s!%s    %s\n' "$C_YELLOW" "$C_RESET" "$*"; }
err()  { printf '  %sx%s    %s\n' "$C_RED" "$C_RESET" "$*" >&2; }
die()  { printf '%s%s: erro:%s %s\n' "$C_RED" "$PROGNAME" "$C_RESET" "$*" >&2; exit 1; }

usage() { cat "$SCRIPT_DIR/HELP.txt"; }
