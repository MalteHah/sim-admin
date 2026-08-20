#!/bin/sh
set -eu

usage() {
    printf 'Aufruf: %s ZIELVERZEICHNIS\n' "$0"
    printf 'Erzeugt einen passwortgeschützten Ed25519-Release-Schlüssel samt öffentlichem Schlüssel und Fingerabdruck.\n'
}

case "${1:-}" in
    --help|-h) usage; exit 0 ;;
    "") usage >&2; exit 2 ;;
esac
[ "$#" -eq 1 ] || { usage >&2; exit 2; }

TARGET=$1
PRIVATE_KEY="$TARGET/sim-admin-release-signing-key.pem"
PUBLIC_KEY="$TARGET/sim-admin-release-signing-key.pub.pem"
FINGERPRINT="$TARGET/sim-admin-release-signing-key.fingerprint.txt"

command -v openssl >/dev/null 2>&1 || { printf 'OpenSSL fehlt.\n' >&2; exit 1; }
[ -d "$TARGET" ] || { printf 'Zielverzeichnis existiert nicht: %s\n' "$TARGET" >&2; exit 1; }
[ -w "$TARGET" ] || { printf 'Zielverzeichnis ist nicht beschreibbar: %s\n' "$TARGET" >&2; exit 1; }

for FILE in "$PRIVATE_KEY" "$PUBLIC_KEY" "$FINGERPRINT"; do
    [ ! -e "$FILE" ] || { printf 'Abbruch: Datei existiert bereits: %s\n' "$FILE" >&2; exit 1; }
done

printf 'Der private Schlüssel wird mit AES-256 verschlüsselt.\n'
printf 'Das jetzt abgefragte Passwort wird nicht gespeichert.\n\n'
umask 077
if [ -n "${SIM_ADMIN_KEY_PASSWORD_FILE:-}" ]; then
    [ -f "$SIM_ADMIN_KEY_PASSWORD_FILE" ] || { printf 'Passwortdatei fehlt.\n' >&2; exit 1; }
    openssl genpkey -algorithm ED25519 -aes-256-cbc -pass "file:$SIM_ADMIN_KEY_PASSWORD_FILE" -out "$PRIVATE_KEY"
    openssl pkey -in "$PRIVATE_KEY" -passin "file:$SIM_ADMIN_KEY_PASSWORD_FILE" -pubout -out "$PUBLIC_KEY"
else
    openssl genpkey -algorithm ED25519 -aes-256-cbc -out "$PRIVATE_KEY"
    openssl pkey -in "$PRIVATE_KEY" -pubout -out "$PUBLIC_KEY"
fi
chmod 0600 "$PRIVATE_KEY"
chmod 0644 "$PUBLIC_KEY"

FINGERPRINT_VALUE=$(openssl pkey -pubin -in "$PUBLIC_KEY" -outform DER | openssl dgst -sha256 -r | awk '{print $1}')
{
    printf 'SIM-Admin Release-Schlüssel\n'
    printf 'Algorithmus: Ed25519\n'
    printf 'SHA-256-Fingerabdruck: %s\n' "$FINGERPRINT_VALUE"
} > "$FINGERPRINT"
chmod 0644 "$FINGERPRINT"

if openssl pkey -in "$PRIVATE_KEY" -passin pass: -noout >/dev/null 2>&1; then
    printf 'Sicherheitsprüfung fehlgeschlagen: Schlüssel ist ohne Passwort lesbar.\n' >&2
    exit 1
fi

printf '\nRelease-Schlüssel erfolgreich erzeugt.\n'
printf 'Privater Schlüssel: %s\n' "$PRIVATE_KEY"
printf 'Öffentlicher Schlüssel: %s\n' "$PUBLIC_KEY"
printf 'Fingerabdruck: %s\n' "$FINGERPRINT_VALUE"
printf '\nDen privaten Schlüssel und sein Passwort niemals auf dem Standalone-Rechner speichern.\n'
