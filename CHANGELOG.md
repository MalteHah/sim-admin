# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.

## Unreleased – Zielversion 0.2.0

Der aktuelle Stand ist noch nicht als stabiles Release freigegeben. Offene
Hardware- und Bereitstellungstests stehen in `docs/testing-and-roadmap.md`.

### Changed

- Projektlizenz auf GPL-3.0-or-later festgelegt

### Added

- Explizite Auswahl der SUCI-Berechnung im Endgerät oder auf einer S17-USIM;
  der USIM-Modus prüft `DF.SAIP` vor dem ersten Schreibzugriff und erlaubt nur
  Profile B mit unkomprimiertem P-256-Schlüssel
- Korrekte UST-Kombination für S17-USIM-Berechnung: Dienste 124 und 125 müssen
  gemeinsam aktiv sein; der Endgeräte-Modus verwendet 124 aktiv und 125 inaktiv
- Vollständiges Auslesen und priorisiertes Anzeigen mehrerer Einträge aus
  `EF.SUCI_Calc_Info`; bestehende Einzel-SUCI-Profile bleiben kompatibel
- Rein lesender Kartenabgleich für ACC und MSISDN mit feldgenauer Anzeige und
  selektiver Übernahme in eine neue verschlüsselte Tresorrevision
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
- Rein lesender SUCI-Kartenabgleich von Routing Indicator, Schutzverfahren, HN-Key-ID, öffentlichem Schlüssel und UST 124/125 gegen das Tresorprofil
- Erfolgreiche Ende-zu-Ende-Tests von Null Scheme, Profile A und Profile B bis zur jeweils abgeschlossenen Open5GS-Registrierung
- Schreibfreigabe `SIM SCHREIBEN` erst nach bewusster Wahl des tatsächlichen SIM-Schreibvorgangs statt bereits bei der Entwurfsvorbereitung
- Browserübergreifend zuverlässiges Ausblenden von mit `hidden` markierten Formularelementen
- Eindeutige HN-Schlüsselprofilauswahl mit automatischer Feldübernahme und gesperrten Schlüsselfeldern bei Null Scheme
- Erfolgreicher Hardwaretest des IMS-Schreibpfads für IMPI, IMPU, IMS-Domain und IST einschließlich Rücklesen und Tresorrevision
- Definierte, zurückgelesene Löschsemantik für IMPI, IMPU, IMS-Domain und IST statt Abbruch bei leeren IMS-Zielwerten
- Rein lesender IMS-Kartenabgleich von IMPI, IMPU, IMS-Domain und IST einschließlich korrekt erkanntem Leerzustand
- Feldgenaue, redigierte Validierungsmeldungen im Einzelkarten-Dry-Run statt einer pauschalen Fehlermeldung
- Korrekte Behandlung deaktivierter optionaler SUCI-Zahlenfelder als leer statt irrtümlich als Null Scheme
- Eindeutige Klassifizierung einer von pySim als Ausnahme gemeldeten ADM1-Ablehnung ohne Wiederholung des Kartenversuchs
- Keine Phantomänderungen mehr zwischen `null` und leer bei optionalen 5GS-Feldern sowie vollständige SUCI-Zielprüfung vor dem ersten Feldschreibzugriff
- Simulierter Sicherheitstest für nicht unterstützte Kartentypen mit unveränderter Revision und erhaltenem Änderungsentwurf
- Simulierter Abbruch bei unpassender IST-Dateigröße mit verständlicher Aktivitätsmeldung und unverändertem Tresorstand
- Einzelkarten-Abgleich direkt unter der Vorschau statt am unteren Rand der hohen Eingabemaske
- Passwortgeschützte selektive Übernahme abweichender, erneut gelesener IMS-Felder und vollständiger SUCI-Konfiguration als neue Tresorrevision ohne SIM-Schreibzugriff
- Klare Unterscheidung zwischen nicht im Tresor verwalteten und tatsächlich abweichenden IMS-/SUCI-Werten; UST 124/125 beeinflussen Null Scheme nicht
- Präzise Anzeige leerer IMS-Kartenfelder und des gültigen, schlüssellosen Null-Scheme-Standardzustands ohne unnötiges Übernahmeangebot
- Werkseitiger, allein vorhandener IST-Servicewert gilt nicht als Teilnehmer-IMS-Konfiguration und löst keine Übernahmeaktion aus
- Übernahmeaktion berücksichtigt einen technischen Vergleichsunterschied nur bei tatsächlich verwalteten Feldern
- Erfolgreicher Hardwaretest der selektiven Übernahme einer abweichenden IMS-Domain als neue Tresorrevision ohne SIM-Schreibzugriff
- Karten-Roadmap in Revision 1 und Revision 2 priorisiert und ADM1-Änderungen verbindlich aus dem Funktionsumfang ausgeschlossen
- Kurze, nicht sensible Änderungsnotiz je Profilrevision; bestehende Revisionen werden neutral gekennzeichnet
