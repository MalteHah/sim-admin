# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.

## Unreleased – Zielversion 0.2.0

Der aktuelle Stand ist noch nicht als stabiles Release freigegeben. Offene
Hardware- und Bereitstellungstests stehen in `docs/testing-and-roadmap.md`.

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
- Geschützte Neuinstallation mit Vorschau, eigenem Dienstkonto, TLS, Zugangsdaten, Tests und systemd-Diensten
- Reproduzierbarer Release-Bau mit Versionsdatei, Dateimanifest, SHA-256-Prüfsumme und taggesteuertem GitHub-Release
- Optionale Ed25519-Signatur und eigenständige Offline-Prüfung gegen einen bereits vertrauenswürdig hinterlegten öffentlichen Release-Schlüssel
- Interaktive, AES-256-geschützte Erstellung und fingerabdruckgesicherte Installation des Release-Vertrauensankers
- Rein lesende Offline-Updateprüfung für Signatur, Manifest, Einzeldateien, Versionsfolge, Archivpfade und Speicherplatz
- Linux-Wheelpaket mit sämtlichen Python-Abhängigkeiten für netzwerkfreie Installation und spätere USB-Updates
- Optionale IMS-Felder IMPI, IMPU, IMS-Domain und IST in CSV-Import, verschlüsseltem Profiltresor und Änderungsentwürfen
- Kontrollierter, zurückgelesener IMS-Schreibpfad für eindeutig erkannte SysmocomSJA5-Karten
- Validierte optionale 5GS-/SUCI-Felder für Routing Indicator, Protection Scheme und Home-Network-Public-Key-Metadaten
- Kontrollierter, vorab lesend geprüfter und unmittelbar zurückgelesener 5GS-/SUCI-Schreibpfad für eindeutig erkannte SysmocomSJA5-Karten
- Separat verschlüsselte Bestandsverwaltung je Karte mit Status, Ausgabeempfänger, Ausgabedatum und begrenzter Bemerkung ohne Profilrevision
- Einheitliche deutsche Aktivitätsdetails einschließlich dynamischer Revisionsnummern und Karten-/Protokollfehler
- Versionsanzeige aus der zentralen `VERSION`-Datei statt fest codierter API- und Footerwerte
- SJA5-kompatible SUCI-Berechnung im Endgerät über `DF.5GS`, UST-Service 124 und getrennte HN-Key-ID/Listenreferenz
- Eindeutige Oberflächenbezeichnungen für AMF und SUCI Routing Indicator sowie Pflichtprüfung des Routing Indicators
- Zentraler, verschlüsselter SUCI-Heimnetzschlüsselkatalog in den Einstellungen mit PEM-/DER-/Hex-Import, Fingerprint und Verwendungsschutz
- Auswahl aktiver zentraler SUCI-Schlüsselprofile bei Einzelkarte und Profiländerung
- Kompatibilität mit der strukturierten UST-Darstellung aktueller pySim-Versionen und stufenbezogene Schreibfehler
