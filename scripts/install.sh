#!/bin/sh
set -eu

MODE="${1:---check}"
INSTALL_ROOT="${SIM_ADMIN_INSTALL_ROOT:-/opt/sim-admin}"
APP_ROOT="$INSTALL_ROOT/application"
PYSIM_ROOT="${SIM_ADMIN_PYSIM_SOURCE:-$INSTALL_ROOT/pysim}"
ERRORS=0

ok() { printf 'OK     %s\n' "$1"; }
warn() { printf 'HINWEIS %s\n' "$1"; }
fail() { printf 'FEHLER %s\n' "$1"; ERRORS=$((ERRORS + 1)); }

if [ "$MODE" != "--check" ]; then
    printf 'Dieses Skript unterstützt derzeit ausschließlich: %s --check\n' "$0" >&2
    exit 2
fi

printf 'SIM-Admin Installationsprüfung\n'
printf 'Ziel: %s\n\n' "$INSTALL_ROOT"

if [ "$(uname -s)" = "Linux" ]; then ok "Linux erkannt"; else fail "Linux wird benötigt"; fi

if [ -r /etc/os-release ]; then
    . /etc/os-release
    case "${ID:-}:${ID_LIKE:-}" in
        debian:*|ubuntu:*|*:debian*) ok "Debian-basiertes System erkannt (${PRETTY_NAME:-unbekannt})" ;;
        *) fail "Unterstützt wird ein Debian-basiertes System (${PRETTY_NAME:-unbekannt} erkannt)" ;;
    esac
else
    fail "/etc/os-release konnte nicht gelesen werden"
fi

if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
    if python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
        ok "Python $PYTHON_VERSION"
    else
        fail "Python 3.11 oder neuer wird benötigt ($PYTHON_VERSION erkannt)"
    fi
else
    fail "python3 fehlt"
fi

for COMMAND in openssl systemctl; do
    if command -v "$COMMAND" >/dev/null 2>&1; then ok "$COMMAND vorhanden"; else fail "$COMMAND fehlt"; fi
done

if command -v pcscd >/dev/null 2>&1 || [ -x /usr/sbin/pcscd ] || systemctl cat pcscd.socket >/dev/null 2>&1; then
    ok "PC/SC-Dienst installiert"
else
    fail "pcscd fehlt"
fi
if command -v pkg-config >/dev/null 2>&1 && pkg-config --exists libpcsclite 2>/dev/null; then
    ok "PC/SC-Entwicklungsbibliothek vorhanden"
else
    fail "libpcsclite-Entwicklungsbibliothek fehlt"
fi

if [ -d "$APP_ROOT" ]; then
    ok "Bestehendes Anwendungsverzeichnis gefunden"
else
    warn "$APP_ROOT wird bei einer Neuinstallation angelegt"
fi

if [ -e "$PYSIM_ROOT/pySim-shell.py" ]; then
    ok "pySim-Quellverzeichnis gefunden"
else
    warn "pySim muss vor dem ersten Kartenbetrieb separat bereitgestellt werden"
fi

if [ "$ERRORS" -gt 0 ]; then
    printf '\nPrüfung fehlgeschlagen: %s Voraussetzung(en) fehlen. Es wurden keine Änderungen vorgenommen.\n' "$ERRORS" >&2
    exit 1
fi

printf '\nPrüfung erfolgreich. Es wurden keine Änderungen vorgenommen.\n'
