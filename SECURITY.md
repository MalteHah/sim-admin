# Sicherheit

## Sicherheitsmeldungen

Bitte Sicherheitslücken nicht als öffentliches GitHub-Issue melden. Nutze die
private Security-Advisory-Funktion des GitHub-Repositorys und beschreibe dort
Auswirkung, betroffene Version und nachvollziehbare Reproduktionsschritte.

## Geheimnisse und Teilnehmerdaten

Folgende Daten dürfen niemals in Git, Issues, Logs oder Screenshots gelangen:

- Ki, OPc, ADM1, PIN und PUK
- Produktions-ICCID, IMSI und MSISDN
- Geräteschlüssel und Sitzungsgeheimnisse
- Passwort-Hashes, TLS-Privatschlüssel und Backup-Passwörter
- Profiltresor-, Aktivitäts- und Backup-Dateien

Vor jeder Veröffentlichung sind Änderungen auf solche Inhalte zu prüfen.

## Unterstützter Betrieb

Die Anwendung ist für einen lokalen Offline-Standalone-Rechner vorgesehen.
Schreibzugriffe auf SIM-Karten erfordern Kartenabgleich, ADM1, erneute
Passwortbestätigung und explizite Freigabe. Ki/OPc-Schreibzugriffe sind derzeit
nur für eindeutig erkannte SysmocomSJA5-Karten vorgesehen.
