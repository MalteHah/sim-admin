# Projektchronik

Diese Chronik dokumentiert die fachlichen und technischen Meilensteine von
`sim-admin`. Sie wird zusammen mit der Anwendung versioniert. Passwörter,
Geräteschlüssel, SIM-Geheimnisse und andere Zugangsdaten gehören ausdrücklich
nicht in dieses Dokument.

## 2026-08-18 – Projektgrundlage

- Eigenständiges Python-Projekt mit FastAPI und klarer Schichtenstruktur angelegt.
- Lokale Weboberfläche, Health-Endpunkt, Tests und Architekturgrundlagen ergänzt.
- Standalone-Betrieb als Systemdienst mit HTTPS und HTTP-Weiterleitung eingerichtet.
- Passwortgeschützte Sitzungen und lokale Passwortänderung umgesetzt.

## 2026-08-18 – Read-only Kartenbetrieb

- PC/SC-Lesererkennung integriert.
- Lesenden pySim-Adapter für ATR, Kartentyp, ICCID und IMSI angebunden.
- Hardwarezugriffe hinter austauschbaren Adaptern gekapselt.
- Dry Run und Kartenabgleich technisch ohne SIM-Schreibpfad umgesetzt.

## 2026-08-18 – Sicherheit und Nachvollziehbarkeit

- Metadatenbasiertes Aktivitätsprotokoll eingeführt.
- Protokollierung von SIM-Geheimnissen, Formularinhalten und Teilnehmerkennungen
  ausgeschlossen.
- Aktivitätenansicht mit Seitennavigation ergänzt.
- Gerätegebundener AES-256-GCM-Schlüssel für den lokalen Profiltresor eingeführt.
- Tresordatenbank und Schlüsseldatei werden mit Dateirechten `0600` geschützt.

## 2026-08-18 – Backup und Wiederherstellung

- USB-Datenträger-Erkennung ergänzt.
- Passwortgeschützte `.sab`-Backups mit AES-256-GCM und scrypt umgesetzt.
- Manifest, Formatversion und SHA-256-Prüfsummen hinzugefügt.
- Zweistufige Prüfung und bestätigungspflichtige Wiederherstellung umgesetzt.
- Aktivitätsprotokoll, verschlüsselter Profiltresor und Geräteschlüssel in das
  Backup aufgenommen.
- Backup und Wiederherstellung auf dem Standalone-System praktisch geprüft.

## 2026-08-18 – CSV-Import und Profiltresor

- Validierungsvorschau ohne Speicherung oder Karten-Schreibzugriff erstellt.
- sysmocom-Schema einschließlich `ADM1`, PIN/PUK und KIC/KID/KIK unterstützt.
- Numbers-Titelzeilen, Leerzeilen, Abschlussnotizen, UTF-8-BOM sowie Komma-,
  Semikolon- und Tabulatortrennung berücksichtigt.
- Leere sysmocom-CSV-Vorlage und feldgenaue, redigierte Fehlerausgabe ergänzt.
- Validierte Profile vollständig verschlüsselt in den Profiltresor übernommen.
- Read-only Tresorübersicht, Seitennavigation, Sortierung und ICCID-/IMSI-Suche
  ergänzt.
- Dry Run und Kartenabgleich direkt aus einem Tresorprofil ermöglicht.
- Zeitlich begrenzte Geheimnisanzeige mit erneuter Passwortbestätigung umgesetzt.
- Redigierten Inventarexport ohne Schlüsselwerte ergänzt.
- Bestehende Tresorprofile als verschlüsselte Revision 1 in eine append-only
  Revisionshistorie übernommen.
- Verschlüsselte Änderungsentwürfe für IMSI, MSISDN, ACC, Ki und OPc ergänzt.
- ICCID und ADM1 in der Änderungsoberfläche fest gesperrt; Entwürfe verändern
  weder das aktive Profil noch dessen Revision oder die SIM-Karte.
- Vorgemerkte Änderungen in der Profilübersicht kenntlich gemacht und eine
  passwortgeschützte Verwerffunktion ergänzt.
- Änderungsentwürfe können vor einem späteren Schreibvorgang als vollständig
  redigierter Dry Run ohne Karten-Schreibzugriff geprüft werden.
- ICCID und IMSI einer eingelegten Karte können ausschließlich lesend gegen den
  vorgemerkten Zielzustand abgeglichen werden.
- Kontrollierten SIM-Schreibpfad für IMSI, ACC und MSISDN ergänzt: erneute
  Anmeldung, exakte Schreibfreigabe, zwingender ICCID-Abgleich, ADM1-Prüfung,
  Zurücklesen und erst danach Übernahme als neue Profilrevision.
- Ki- und OPc-Änderungen werden nur auf eindeutig erkannten SysmocomSJA5-Karten
  zugelassen. USIM- und 2G-Authentisierungsdateien werden als Milenage/OPc
  geschrieben, unmittelbar zurückgelesen und intern verglichen; andere
  Kartentypen bleiben blockiert.

## Festgelegte Regeln für spätere Schreibvorgänge

- ICCID und ADM1 gelten nach dem Import als unveränderbar.
- Andere Profilfelder dürfen kontrolliert angepasst werden.
- Änderungen werden erst nach einem erfolgreichen SIM-Schreibvorgang übernommen.
- Fehlgeschlagene Schreibvorgänge verändern den Tresoreintrag nicht.
- Profile erhalten nachvollziehbare Revisionen; Geheimwerte erscheinen nicht im
  Aktivitätsprotokoll.
- Das Datenmodell bleibt für IMS-, SUCI- und weitere 5G-Felder erweiterbar.
- Eine interne Profil-ID bleibt unabhängig von der ICCID.

## 2026-08-18 – Einzelkartenerfassung

- Den bisherigen manuellen Provisionierungsbereich in „Einzelkarte“ umbenannt.
- ICCID und IMSI werden direkt von der eingelegten Karte gelesen und gegen den
  Profiltresor geprüft.
- Bekannte ICCIDs führen zum bestehenden Profil und erzeugen keine Dublette.
- Unbekannte Karten können nach Dry Run und erneuter Passwortbestätigung als
  verschlüsselte Revision 1 aufgenommen werden; die SIM bleibt dabei unverändert.
- Alternativ können Profildaten vor Verfügbarkeit der Karte vorbereitet werden.
  Solche Profile bleiben sichtbar als „Kartenabgleich ausstehend“ markiert.
- Ein erfolgreicher read-only ICCID-Abgleich bindet den Datensatz an die passende
  Karte; eine abweichende ICCID kann den Status nicht freigeben.
- Profile können nach erneuter Anmeldung und exakter ICCID-Bestätigung vollständig
  gelöscht werden. Dabei werden auch Revisionen und Änderungsentwürfe entfernt;
  eine Wiederherstellung ist anschließend nur aus einem Backup möglich.
- Die Tresoransicht kann nach Kartenprüfung, ausstehendem Kartenabgleich und
  vorgemerkten Änderungen gefiltert werden; Kartenabgleiche aktualisieren den
  sichtbaren Status unmittelbar.
- Vorbereitete Datensätze erhalten eine eigene read-only Aktion „Karte zuordnen“;
  eine abweichende IMSI ist dabei zulässig, eine abweichende ICCID blockiert die
  Zuordnung. Neue Sicherheitsvorgänge werden im Aktivitätsprotokoll verständlich
  bezeichnet.

## Bereitstellung und Wartung

- GitHub-Repository, Releasebau und versionierte Dokumentation sind vorhanden.
- Das reproduzierbare Neuinstallationsskript ist implementiert; der VM-Test ist offen.
- Signierte Offline-Pakete und deren rein lesende USB-Prüfung sind implementiert.
- Vor Updates automatisch sichern, Version und Schema prüfen und bei Fehlern zur
  vorherigen Version zurückkehren.
- Benutzer-, Administrator-, Entwicklungs-, Architektur- und API-Dokumentation
  gemeinsam mit jeder Anwendungsversion veröffentlichen.
- Private Release-Signierschlüssel ausschließlich getrennt vom Repository und
  vom Standalone-Rechner verwahren; dort liegt nur der öffentliche Vertrauensanker.

## 2026-08-20 – Optionale IMS-Profildaten

- IMPI, IMPU, IMS-Domain und IST als optionale, validierte Profilfelder ergänzt.
- IMS-Felder aus CSV-Dateien werden gemeinsam mit dem übrigen Profil
  gerätegebunden verschlüsselt und niemals im Klartext in SQLite abgelegt.
- Bestehende Profile ohne IMS-Daten bleiben ohne Datenmigration les- und
  bearbeitbar.
- Änderungsentwürfe können IMS-Daten vormerken. Auf eindeutig erkannten
  SysmocomSJA5-Karten werden EF.IMPI, EF.IMPU, EF.DOMAIN und EF.IST erst nach
  ICCID-/ADM1-Prüfung geschrieben, zurückgelesen und anschließend revisioniert.

## Noch nicht umgesetzt

- Unterstützung weiterer Kartentypen für Ki und OPc.
- Zusätzliche kartentypabhängig lesbare Felder über ACC und MSISDN hinaus.
- Produktive Updateausführung mit Vorab-Backup und Rollback.

## Priorisierte Karten-Roadmap

- Revision 1 ist funktional umgesetzt: SUCI-Berechnung auf der USIM, mehrere
  SUCI-Konfigurationen mit Prioritäten sowie ACC-/MSISDN-Vergleich und
  selektive Übernahme. Die Mehrfachkonfiguration wurde auf Karte 900001 mit
  Profile B, HN-Key-ID 2 und erfolgreicher Open5GS-Registrierung abgenommen.
- Revision 2: weitere Kartentypen, S17-spezifische Parameter, weitere
  kartenspezifische SUCI-Varianten, erweiterte IMS-Strukturen,
  Stapelverarbeitung und Wiederaufnahme unterbrochener Schreibvorgänge.
- ADM1 bleibt unveränderbar: Es wird ausschließlich zur Autorisierung geprüft
  und niemals von SIM-Admin gelesen, geändert, entsperrt oder geschrieben.

## 2026-08-20 – Beginn der 5GS-/SUCI-Erweiterung

- Optionale CSV-Felder `routing_indicator`, `protection_scheme`,
  `hn_public_key_id` und `hn_public_key` mit strikter Formatprüfung ergänzt.
- Die Werte werden beim Import wie alle Profildaten ausschließlich im
  verschlüsselten Datensatz abgelegt.
- Auf eindeutig erkannten SysmocomSJA5-Karten werden EF.Routing_Indicator unter
  DF.5GS und die für die Endgeräteberechnung verwendete EF.SUCI_Calc_Info unter
  DF.5GS vor jedem Schreibvorgang lesend geprüft. Erst danach werden die Werte
  geschrieben und unmittelbar zurückgelesen. Eine neue Tresorrevision entsteht
  nur nach vollständiger Bestätigung.

## 2026-08-21 – SUCI-Ende-zu-Ende-Abnahme

- Null Scheme, Profile A (X25519, HN-Key-ID 1) und Profile B (P-256,
  HN-Key-ID 2) wurden auf einer SysmocomSJA5 erfolgreich programmiert und
  zurückgelesen.
- Open5GS löste alle drei SUCI-Varianten zur erwarteten IMSI auf und schloss die
  5G-Registrierung erfolgreich ab.
- Der Profiltresor erhielt einen rein lesenden Vergleich der SUCI-Kartendaten
  einschließlich Routing Indicator, Scheme, Key-ID, Public Key und UST 124/125.

## 2026-08-21 – IMS-Kartenschreibtest

- IMPI, IMPU, IMS-Domain und IST wurden auf einer separaten SysmocomSJA5-
  Testkarte programmiert und unmittelbar erfolgreich zurückgelesen.
- Die aktive Tresorrevision wurde erst nach vollständiger Bestätigung aller vier
  ISIM-Felder angelegt.
- Die spätere IMS-Netzregistrierung bleibt vom Aufbau des Kamailio-IMS-Systems
  abhängig und ist nicht Bestandteil dieses Kartenschreibtests.
- Leere IMS-Zielwerte wurden anschließend als echter Löschvorgang geprüft:
  IMPI, IMPU und Domain wurden geleert, IST-Dienste deaktiviert und alle Werte
  zurückgelesen. Ein vorausgehender Fehler erzeugte erwartungsgemäß keine neue
  Revision und der Entwurf konnte nach der Korrektur erneut ausgeführt werden.

## 2026-08-21 – Selektive Kartenübernahme

- Eine IMS-Domain wurde kontrolliert ausschließlich auf einer Testkarte gesetzt,
  während der verschlüsselte Tresoreintrag unverändert blieb.
- Der Kartenabgleich erkannte genau diese Abweichung. Nach erneuter Kartenlesung
  und Passwortprüfung wurde nur die IMS-Domain als neue Tresorrevision übernommen.
- Der Übernahmevorgang selbst führte keinen Schreibzugriff auf die SIM aus;
  ICCID, Ki, OPc und ADM1 blieben grundsätzlich ausgeschlossen.

## 2026-08-23 – Freigabe 1.0.0

- Kartenrevision 1 mit S17-USIM-SUCI, priorisierten Mehrfachkonfigurationen und
  selektiver Übernahme weiterer lesbarer Kartendaten abgeschlossen.
- SUCI-Mehrfachkonfiguration auf Karte 900001 bis zur erfolgreichen
  Open5GS-Registrierung hardwareseitig abgenommen.
- Optionalen Service Provider Name (SPN) mit verschlüsselter Speicherung,
  Kartenvergleich, Übernahme sowie kontrolliertem Schreib- und Rücklesepfad
  ergänzt und auf einer Karte geprüft.
- Realistisches verschlüsseltes USB-Backup mit Profilen, Revisionen,
  Bestandsdaten, SUCI-Schlüsselkatalog, Aktivitätsprotokoll, Tresorschlüssel und
  SPN vollständig auf Integrität und Entschlüsselbarkeit geprüft.
- Version 1.0.0 als stabile Freigabe des bestehenden Standalone-Kartenbetriebs
  dokumentiert. Neuinstallation und produktive Offline-Updates bleiben bis zur
  gesonderten VM-Abnahme ausdrücklich nicht freigegeben.

## 2026-08-26 – Installationskorrektur 1.0.1

- Beim ersten Test auf einem separaten Debian-13-Minirechner fehlende und
  zusammengefasste Paketvoraussetzungen sichtbar gemacht.
- Voraussetzungstest auf eindeutige Debian-Paketnamen und unterschiedliche
  Anforderungen für vollständige Offline-Releases beziehungsweise Quellbauten
  umgestellt.
- Den auf der Referenz-VM getesteten pySim-Commit
  `9c77e4ed948e97584680a0b1c1a630bc7fa6bfcd` samt eingefrorenen Wheels in den
  reproduzierbaren Release-Bau aufgenommen.
- Automatische getrennte pySim-Installation und Bereinigung abgebrochener
  Erstinstallationen ergänzt.
