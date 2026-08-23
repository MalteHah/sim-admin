# Release Notes – SIM-Admin 1.0.0

Freigabe: 23. August 2026

## Einordnung

Version 1.0.0 ist die erste stabile Freigabe des auf der bestehenden
Standalone-VM betriebenen Kartenverwaltungs- und Personalisierungsumfangs. Sie
deckt den lokalen Arbeitsablauf von CSV-Import oder Einzelkartenerfassung über
den verschlüsselten Profiltresor bis zum kontrollierten, zurückgelesenen
SIM-Schreibvorgang ab.

## Enthalten

- Passwortgeschützte Offline-Webanwendung mit HTTPS und PC/SC-Lesererkennung.
- Validierter sysmocom-CSV-Import und Einzelkartenerfassung in zwei Arbeitsweisen.
- Gerätegebundener AES-256-GCM-Profiltresor mit Revisionen, Entwürfen,
  Bestandsverwaltung, Suche, Sortierung, Filter und redigiertem Export.
- Kontrolliertes Schreiben und Rücklesen von IMSI, ACC, MSISDN und SPN.
- Kartentypspezifisches Schreiben von Ki/OPc sowie IMS- und 5GS-/SUCI-Feldern
  auf eindeutig erkannten SysmocomSJA5-Karten.
- SUCI-Berechnung im Endgerät mit bis zu acht priorisierten Schutzverfahren oder
  auf einer S17-USIM mit Profile B.
- Zentraler, verschlüsselter Katalog öffentlicher SUCI-Heimnetzschlüssel.
- Rein lesender, feldgenauer Kartenabgleich und selektive Übernahme geeigneter
  Kartendaten in eine neue Tresorrevision.
- AES-256-GCM-verschlüsselte USB-Backups mit Manifest, Prüfsummen,
  Profiltresorschlüssel und bestätigungspflichtiger Wiederherstellung.
- Metadatenbasiertes Aktivitätsprotokoll ohne Teilnehmerkennungen oder
  SIM-Geheimnisse.

## Abgenommen

- Null Scheme, Profile A und Profile B bis zur erfolgreichen
  Open5GS-Registrierung.
- SUCI-Berechnung auf einer S17-USIM sowie Mehrfachkonfiguration mit Auswahl von
  Profile B und HN-Key-ID 2.
- IMS-Schreiben und -Löschen mit unmittelbarem Rücklesen.
- SPN-Schreiben und Rücklesen.
- Sicherheitsabbrüche bei fehlender beziehungsweise falscher Karte,
  abgewiesener ADM1 und nicht unterstütztem Kartentyp.
- Inhalts- und Integritätsprüfung eines realistischen Backups mit 20 Profilen,
  42 Revisionen, Bestandsdaten, SUCI-Schlüsselkatalog, Aktivitätsprotokoll,
  Tresorschlüssel und SPN.
- Vollständige automatisierte Testsuite auf der Standalone-VM.

## Bekannte Einschränkungen

- Die Neuinstallation aus dem Release-Paket ist implementiert, aber noch nicht
  auf der vorbereiteten Test-VM abgenommen.
- Die Offline-Updateprüfung ist rein lesend. Produktiver Austausch,
  automatisches Vorab-Backup und Rollback sind noch nicht implementiert.
- Weitere Hersteller und Kartentypen, zusätzliche S17-Dateien, erweiterte
  IMS-Strukturen, Stapelverarbeitung und Wiederaufnahme unterbrochener
  Schreibvorgänge gehören zur Kartenrevision 2.
- ADM1 wird absichtlich niemals gelesen, geändert, entsperrt oder geschrieben.
- Netzseitige IMS-Systeme sind nicht Bestandteil dieser Freigabe.

## Backup-Hinweis

Das Anwendungsbackup enthält Profiltresor, Revisionen, Entwürfe,
Bestandsverwaltung, SUCI-Schlüsselkatalog, Aktivitätsprotokoll und
Profiltresorschlüssel. Betriebssystem, Anmeldepasswort, TLS-Schlüssel,
Release-Vertrauensanker und Programmdateien sind nicht enthalten.
