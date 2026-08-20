#!/bin/sh
set -eu

[ "$#" -eq 2 ] || {
    printf 'Aufruf: %s ÖFFENTLICHER_SCHLÜSSEL ERWARTETER_SHA256_FINGERABDRUCK\n' "$0" >&2
    exit 2
}
[ "$(id -u)" -eq 0 ] || { printf 'Administratorrechte sind erforderlich.\n' >&2; exit 1; }

SOURCE=$1
EXPECTED=$2
TARGET=/etc/sim-admin/release-signing-key.pub.pem
[ -f "$SOURCE" ] || { printf 'Öffentlicher Schlüssel fehlt: %s\n' "$SOURCE" >&2; exit 1; }
[ ! -e "$TARGET" ] || { printf 'Abbruch: Ein Release-Vertrauensanker ist bereits hinterlegt.\n' >&2; exit 1; }

ACTUAL=$(openssl pkey -pubin -in "$SOURCE" -outform DER | openssl dgst -sha256 -r | awk '{print $1}')
[ "$ACTUAL" = "$EXPECTED" ] || { printf 'Fingerabdruck stimmt nicht überein.\n' >&2; exit 1; }

install -d -m 0755 -o root -g root /etc/sim-admin
install -m 0644 -o root -g root "$SOURCE" "$TARGET"
printf 'Release-Vertrauensanker installiert. SHA-256: %s\n' "$ACTUAL"
