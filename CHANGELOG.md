# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.

## Unreleased

### Changed

- Projektlizenz auf GPL-3.0-or-later festgelegt

### Added

- Initiales Python- und FastAPI-Projektgrundgerüst
- Minimaler API- und Health-Endpunkt
- Architekturübersicht für die spätere pySim-Integration
- Validierte Domänenmodelle für Reader, SIM, IMS und 5GS
- Verdeckte Darstellung sensibler SIM-Zugangsdaten
- PC/SC-Reader-Erkennung hinter einer austauschbaren Adapter-Schnittstelle
- API-Endpunkt `GET /api/v1/readers`
- Lokales Dashboard mit automatischer Reader-Statusanzeige
- Passwortgeschützte Weboberfläche mit signierten, zeitlich begrenzten Sitzungen
- Geschütztes, ausschließlich lesendes Auslesen von Kartentyp, ATR, ICCID und IMSI
- Einstellungsseite zum sicheren Ändern des Anmeldepassworts
- HTTPS-Betrieb mit sicheren Sitzungscookies und HTTP-Weiterleitung
- Validierter, vollständig redigierter Provisionierungs-Dry-Run ohne Hardwarezugriff
- Read-only Kartenabgleich von ICCID und IMSI gegen den Provisionierungsentwurf
- Metadatenbasiertes Aktivitätsprotokoll ohne SIM-Geheimnisse oder Formulardaten
- AES-256-GCM-verschlüsselte, verifizierte Backups auf eingebundene Wechseldatenträger
- Validierungsvorschau für CSV-Importe ohne Speicherung oder SIM-Schreibzugriff
- Downloadbare sysmocom-CSV-Vorlage und feldgenaue, redigierte Importfehler
- Gerätegebundener, AES-256-GCM-verschlüsselter Profiltresor für validierte CSV-Importe
- Read-only Tresorübersicht ohne Übertragung von Schlüssel- oder Zugangsdaten
- Dry Run und read-only Kartenabgleich direkt aus verschlüsselten Tresorprofilen
- ICCID-/IMSI-Sortierung und oberhalb der Liste platzierte Aktionsmeldungen
- Zeitlich begrenzte Geheimnisanzeige nach erneuter Passwortbestätigung
- Kombinierte ICCID-/IMSI-Suche im Profiltresor
- Redigierter CSV-Inventarexport ohne Schlüssel- oder Zugangsdaten
- Verschlüsselte, append-only Profilrevisionen als Grundlage für spätere Änderungen
- Read-only Revisionshistorie in der Profiltresor-Oberfläche
- Gerätegebunden verschlüsselte Änderungsentwürfe für veränderbare Profilfelder
- Gesperrte ICCID und ADM1 sowie unveränderte aktive Revision bis zum späteren erfolgreichen SIM-Schreibvorgang
- Sichtbare Kennzeichnung vorgemerkter Änderungen und passwortgeschütztes Verwerfen von Entwürfen
- Erneutes Laden der nicht geheimen Entwurfswerte beim Öffnen der Änderungsmaske
- Redigierter Dry Run für den verschlüsselt gespeicherten Änderungsentwurf
- Ausschließlich lesender Kartenabgleich gegen den vorgemerkten Zielzustand
- Passwort- und bestätigungsgeschützter SIM-Schreibpfad für IMSI, ACC und MSISDN
- Zwingender ICCID-Abgleich, ADM1-Verifikation, Rücklesen und Revisionierung erst nach vollständiger Bestätigung
- Sichere Sperre für Ki-/OPc-Änderungen auf nicht unterstützten Kartentypen
- Ausblenden der Passwortfreigabe nach erfolgreichem Öffnen der Geheimnisansicht
- Umbenennung der manuellen Provisionierung in „Einzelkarte“
- Read-only Kartenerkennung mit Dublettenprüfung und verschlüsselter Einzelerfassung als Revision 1
- Korrigierter Abstand des Profiltresor-Links in der Einzelkartenansicht
- Zwei Einzelkartenmodi „Karte zuerst“ und „Daten zuerst“
- Sichtbarer Status für kartengeprüfte Profile und noch ausstehende Kartenabgleiche
- Passwort- und ICCID-bestätigtes Löschen eines Profils samt Revisionen und Änderungsentwurf
- Statusfilter im Profiltresor und sofortige Aktualisierung nach erfolgreichem Kartenabgleich
- Eigene „Karte zuordnen“-Aktion für vorbereitete Profile und verständliche Bezeichnungen neuer Aktivitäten
- Kartentypspezifisches, zurückgelesenes Schreiben von Ki und OPc auf SysmocomSJA5-USIMs
- Passwortgeschützte Übernahme einer abweichenden Karten-IMSI als neue Tresorrevision ohne SIM-Schreibzugriff
- Nicht verändernder Installations-Prüfmodus für Debian-, Python-, systemd-, OpenSSL- und PC/SC-Voraussetzungen
