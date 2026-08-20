#!/bin/sh
set -eu

MODE="--check"; DRY_RUN=0
for ARG in "$@"; do
    case "$ARG" in
        --check|--install) MODE="$ARG" ;;
        --dry-run) DRY_RUN=1 ;;
        --help|-h) printf 'Aufruf: %s [--check | --install [--dry-run]]\n' "$0"; exit 0 ;;
        *) printf 'Unbekannte Option: %s\n' "$ARG" >&2; exit 2 ;;
    esac
done

INSTALL_ROOT="${SIM_ADMIN_INSTALL_ROOT:-/opt/sim-admin}"
APP_ROOT="$INSTALL_ROOT/application"
PYSIM_ROOT="${SIM_ADMIN_PYSIM_SOURCE:-$INSTALL_ROOT/pysim}"
SERVICE_USER="${SIM_ADMIN_SERVICE_USER:-sim-admin}"
LOGIN_USER="${SIM_ADMIN_LOGIN_USER:-admin}"
SOURCE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
USERADD=/usr/sbin/useradd
RUNUSER=/usr/sbin/runuser
ERRORS=0

ok() { printf 'OK     %s\n' "$1"; }
warn() { printf 'HINWEIS %s\n' "$1"; }
fail() { printf 'FEHLER %s\n' "$1"; ERRORS=$((ERRORS + 1)); }
plan() { printf 'PLAN   %s\n' "$1"; }

preflight() {
    printf 'SIM-Admin Installationsprüfung\nZiel: %s\n\n' "$INSTALL_ROOT"
    if [ "$(uname -s)" = "Linux" ]; then ok "Linux erkannt"; else fail "Linux wird benötigt"; fi
    if [ -r /etc/os-release ]; then
        . /etc/os-release
        case "${ID:-}:${ID_LIKE:-}" in
            debian:*|ubuntu:*|*:debian*) ok "Debian-basiertes System erkannt (${PRETTY_NAME:-unbekannt})" ;;
            *) fail "Unterstützt wird ein Debian-basiertes System (${PRETTY_NAME:-unbekannt} erkannt)" ;;
        esac
    else fail "/etc/os-release konnte nicht gelesen werden"; fi
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
        if python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then ok "Python $PYTHON_VERSION"; else fail "Python 3.11 oder neuer wird benötigt ($PYTHON_VERSION erkannt)"; fi
        if python3 -m venv --help >/dev/null 2>&1; then ok "Python-venv vorhanden"; else fail "python3-venv fehlt"; fi
    else fail "python3 fehlt"; fi
    for COMMAND in openssl systemctl tar; do
        if command -v "$COMMAND" >/dev/null 2>&1; then ok "$COMMAND vorhanden"; else fail "$COMMAND fehlt"; fi
    done
    if [ -x "$USERADD" ] && [ -x "$RUNUSER" ]; then ok "Systemkonto-Werkzeuge vorhanden"; else fail "useradd oder runuser fehlt"; fi
    if [ -f "$SOURCE_ROOT/requirements.txt" ] && [ -f "$SOURCE_ROOT/app/main.py" ]; then ok "Vollständiges Release-Paket erkannt"; else fail "Das Skript muss aus einem vollständigen SIM-Admin-Release gestartet werden"; fi
    if command -v pcscd >/dev/null 2>&1 || [ -x /usr/sbin/pcscd ] || systemctl cat pcscd.socket >/dev/null 2>&1; then ok "PC/SC-Dienst installiert"; else fail "pcscd fehlt"; fi
    if command -v pkg-config >/dev/null 2>&1 && pkg-config --exists libpcsclite 2>/dev/null; then ok "PC/SC-Entwicklungsbibliothek vorhanden"; else fail "libpcsclite-Entwicklungsbibliothek fehlt"; fi
    if [ -d "$APP_ROOT" ]; then ok "Bestehendes Anwendungsverzeichnis gefunden"; else warn "$APP_ROOT wird bei einer Neuinstallation angelegt"; fi
    if [ -e "$PYSIM_ROOT/pySim-shell.py" ]; then ok "pySim-Quellverzeichnis gefunden"; else warn "pySim muss vor dem ersten Kartenbetrieb separat bereitgestellt werden"; fi
    if [ "$ERRORS" -gt 0 ]; then printf '\nPrüfung fehlgeschlagen: %s Voraussetzung(en) fehlen. Es wurden keine Änderungen vorgenommen.\n' "$ERRORS" >&2; return 1; fi
    printf '\nPrüfung erfolgreich. Es wurden keine Änderungen vorgenommen.\n'
}

show_plan() {
    printf '\nInstallationsvorschau\n'
    plan "Systemkonto '$SERVICE_USER' bereitstellen"
    plan "Anwendung aus '$SOURCE_ROOT' nach '$APP_ROOT' kopieren"
    plan "Python-Umgebung und Abhängigkeiten installieren"
    plan "Geräteschlüssel, Zugangsdaten und selbstsigniertes TLS-Zertifikat erzeugen"
    plan "HTTPS-Dienst :8443 und Weiterleitung :8000 einrichten"
    plan "Tests ausführen und Dienste erst danach aktivieren"
    printf '\nVorschau abgeschlossen. Es wurden keine Änderungen vorgenommen.\n'
}

install_application() {
    if [ "$(id -u)" -ne 0 ]; then printf 'Die Installation muss mit Administratorrechten gestartet werden.\n' >&2; exit 1; fi
    if [ -e "$APP_ROOT" ] || [ -e /etc/sim-admin.env ] || [ -e /etc/systemd/system/sim-admin.service ]; then
        printf 'Eine bestehende Installation wurde erkannt. Das Installationsskript überschreibt sie nicht.\n' >&2; exit 1
    fi
    printf 'Neues Anmeldepasswort für %s: ' "$LOGIN_USER" >&2
    stty -echo; IFS= read -r PASSWORD; stty echo; printf '\n' >&2
    printf 'Passwort wiederholen: ' >&2
    stty -echo; IFS= read -r PASSWORD_REPEAT; stty echo; printf '\n' >&2
    [ "$PASSWORD" = "$PASSWORD_REPEAT" ] || { printf 'Die Passwörter stimmen nicht überein.\n' >&2; exit 1; }
    [ "${#PASSWORD}" -ge 12 ] || { printf 'Das Passwort muss mindestens 12 Zeichen lang sein.\n' >&2; exit 1; }

    if ! id "$SERVICE_USER" >/dev/null 2>&1; then "$USERADD" --system --home-dir "$INSTALL_ROOT" --shell /usr/sbin/nologin "$SERVICE_USER"; fi
    SERVICE_GROUP=$(id -gn "$SERVICE_USER")
    install -d -m 0750 -o "$SERVICE_USER" -g "$SERVICE_GROUP" "$APP_ROOT" "$APP_ROOT/config" "$APP_ROOT/data/database" "$APP_ROOT/data/backups" "$APP_ROOT/data/imports" "$APP_ROOT/data/exports"
    (cd "$SOURCE_ROOT" && tar --exclude=.git --exclude=.venv --exclude=work --exclude=outputs --exclude='data/database/*' --exclude='config/*.key' -cf - .) | (cd "$APP_ROOT" && tar -xf -)
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$APP_ROOT"
    python3 -m venv "$APP_ROOT/.venv"
    "$APP_ROOT/.venv/bin/python" -m pip install --upgrade pip
    "$APP_ROOT/.venv/bin/python" -m pip install -r "$APP_ROOT/requirements.txt"

    install -d -m 0750 -o root -g "$SERVICE_GROUP" /etc/sim-admin/tls
    CREDENTIAL_FILE=/etc/sim-admin/credentials.json
    PASSWORD_HASH=$(printf '%s' "$PASSWORD" | python3 -c 'import hashlib,json,secrets,sys; s=secrets.token_bytes(16); h=hashlib.scrypt(sys.stdin.read().encode(),salt=s,n=2**14,r=8,p=1); print(json.dumps({"password_hash":f"{s.hex()}:{h.hex()}"}))')
    unset PASSWORD PASSWORD_REPEAT
    printf '%s\n' "$PASSWORD_HASH" > "$CREDENTIAL_FILE"
    chown root:"$SERVICE_GROUP" "$CREDENTIAL_FILE"; chmod 0640 "$CREDENTIAL_FILE"
    SESSION_SECRET=$(openssl rand -hex 32)
    cat > /etc/sim-admin.env <<EOF
SIM_ADMIN_USERNAME=$LOGIN_USER
SIM_ADMIN_SESSION_SECRET=$SESSION_SECRET
SIM_ADMIN_CREDENTIAL_FILE=$CREDENTIAL_FILE
SIM_ADMIN_SECURE_COOKIE=true
SIM_ADMIN_PROFILE_DB=$APP_ROOT/data/database/profiles.db
SIM_ADMIN_PROFILE_KEY=$APP_ROOT/config/profile.key
SIM_ADMIN_PYSIM_PYTHON=$INSTALL_ROOT/venv/bin/python
SIM_ADMIN_PYSIM_SOURCE=$PYSIM_ROOT
SIM_ADMIN_HTTPS_PORT=8443
EOF
    chmod 0600 /etc/sim-admin.env
    openssl req -x509 -newkey rsa:3072 -nodes -days 825 -subj "/CN=sim-admin.local" -keyout /etc/sim-admin/tls/server.key -out /etc/sim-admin/tls/server.crt >/dev/null 2>&1
    chmod 0640 /etc/sim-admin/tls/server.key; chown root:"$SERVICE_GROUP" /etc/sim-admin/tls/server.key

    cat > /etc/systemd/system/sim-admin.service <<EOF
[Unit]
Description=sim-admin standalone HTTPS application
After=network.target pcscd.socket
[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$APP_ROOT
EnvironmentFile=/etc/sim-admin.env
ExecStart=$APP_ROOT/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile /etc/sim-admin/tls/server.key --ssl-certfile /etc/sim-admin/tls/server.crt
Restart=on-failure
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
    cat > /etc/systemd/system/sim-admin-redirect.service <<EOF
[Unit]
Description=sim-admin HTTP to HTTPS redirect
After=network.target sim-admin.service
[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$APP_ROOT
Environment=SIM_ADMIN_HTTPS_PORT=8443
ExecStart=$APP_ROOT/.venv/bin/uvicorn app.redirect:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
    "$RUNUSER" -u "$SERVICE_USER" -- "$APP_ROOT/.venv/bin/python" -m pytest -q "$APP_ROOT/tests"
    systemctl daemon-reload
    systemctl enable --now pcscd.socket sim-admin.service sim-admin-redirect.service
    printf '\nInstallation erfolgreich. SIM-Admin ist per HTTPS auf Port 8443 erreichbar.\n'
}

if [ "$MODE" = "--check" ]; then
    [ "$DRY_RUN" -eq 0 ] || { printf '%s\n' '--dry-run ist nur zusammen mit --install zulässig.' >&2; exit 2; }
    preflight
elif [ "$DRY_RUN" -eq 1 ]; then preflight; show_plan
else preflight; install_application
fi
