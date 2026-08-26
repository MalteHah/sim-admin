# Administrationsanleitung

## Betriebsmodell

SIM-Admin ist für einen dedizierten, offline betriebenen Debian-Rechner gedacht.
Die Webanwendung läuft als systemd-Dienst ohne interaktives Benutzerkonto.
pySim und PC/SC werden nur über getrennte Bridge-Prozesse angesprochen.

Standardpfade einer Installation:

| Zweck | Pfad |
| --- | --- |
| Anwendung | `/opt/sim-admin/application` |
| Anwendungsumgebung | `/opt/sim-admin/application/.venv` |
| pySim-Quellen | `/opt/sim-admin/pysim` |
| pySim-Python | `/opt/sim-admin/venv/bin/python` |
| Laufzeitkonfiguration | `/etc/sim-admin.env` |
| TLS-Schlüssel/Zertifikat | `/etc/sim-admin/tls/` |
| Release-Vertrauensanker | `/etc/sim-admin/release-signing-key.pub.pem` |

## Dienste kontrollieren

```bash
sudo systemctl status sim-admin sim-admin-redirect pcscd.socket
sudo journalctl -u sim-admin -n 100 --no-pager
```

Nach einer Konfigurationsänderung:

```bash
sudo systemctl restart sim-admin
```

## Sicherheitsregeln

- `/etc/sim-admin.env`, Zugangsdaten, Geräteschlüssel und TLS-Schlüssel dürfen
  nicht in Git oder Supportausgaben gelangen.
- Der Profiltresor ist gerätegebunden: `profiles.db` und `profile.key` gehören
  zusammen. Der Schlüssel wird deshalb im verschlüsselten USB-Backup gesichert.
- Der zentrale SUCI-Schlüsselkatalog liegt ebenfalls verschlüsselt in
  `profiles.db` und ist damit automatisch Bestandteil des USB-Backups. Er nimmt
  ausschließlich öffentliche HNET-Schlüssel an; der private Open5GS-Schlüssel
  verbleibt auf dem UDM-System.
- Das Backup-Passwort wird nicht gespeichert und kann nicht zurückgesetzt
  werden.
- Der private Release-Schlüssel gehört nicht auf den Standalone-Rechner. Dort
  wird nur der vorher abgeglichene öffentliche Schlüssel installiert.
- Hardware-Schreibtests ausschließlich mit Testkarten und aktuellem Backup.

## Benutzerpasswort

Das Anmeldepasswort wird in der Anwendung unter **Einstellungen** geändert. Die
Änderung wirkt auf neue Anmeldungen; das Passwort soll mindestens zwölf Zeichen
lang und unabhängig vom Backup-Passwort sein.

## Datenpflege

Regelmäßig sollten ein verschlüsseltes USB-Backup erstellt, dessen Integrität
über **Backup prüfen** kontrolliert und der Datenträger anschließend sicher
ausgeworfen werden. Inventarexporte enthalten keine Schlüssel oder ADM-Daten und
ersetzen kein vollständiges Backup.

Bestandsstatus, Ausgabeempfänger, Datum und Bemerkung liegen separat
gerätegebunden verschlüsselt in der Profildatenbank. Sie werden vom regulären
USB-Backup erfasst, erzeugen aber keine neue SIM-Profilrevision.

Wird ein gemounteter USB-Stick in SIM-Admin nicht angeboten, sind Einhängepunkt
und alle Elternverzeichnisse unter dem Dienstkonto zu prüfen. Die
[Backup-Anleitung](standalone/backup-restore.md#eingebundener-usb-stick-wird-nicht-angezeigt)
beschreibt die Diagnose und eine gezielte ACL für `sim-admin`. Der Name des
Datenträgers ist dabei unerheblich; globale Schreib- oder Leserechte sind nicht
erforderlich.

## Versions- und Updatebetrieb

Nur signierte Pakete verwenden. Die Offline-Prüfung verändert keine Dateien und
ist vor jedem späteren Update verpflichtend. Der eigentliche Austausch einer
bestehenden Installation ist in Version 1.0.1 noch nicht freigegeben und muss
erst auf der Test-VM abgenommen werden.

## Störungsfall

Bei einem Fehler keine wiederholten Schreibversuche auf derselben Karte starten.
Zuerst Aktivitätsprotokoll und Dienststatus prüfen, Kartenleser neu verbinden und
den Kartenstand erneut ausschließlich lesen. Fehlermeldungen und Metadaten dürfen
dokumentiert werden; Geheimwerte gehören niemals in Issues oder Chatverläufe.

### Reader nur für SIM-Admin nicht sichtbar

Erscheint der Reader in `pcsc_scan`, während `/api/v1/readers` mit HTTP 503
antwortet, ist das `pcscd`-Journal zu prüfen. Die Meldungen `Rejected
unauthorized PC/SC client` und `NOT authorized for action: access_pcsc` weisen
auf eine fehlende Polkit-Freigabe für das Dienstkonto hin. Die erforderliche,
auf `sim-admin` beschränkte Regel und der Testbefehl sind in der
[Installationsanleitung](standalone/installation.md#reader-unter-debian-13-nicht-sichtbar)
dokumentiert. Polkit lädt die Regel normalerweise ohne Neustart; ein Neustart
der Dienste ist nur eine Ausweichmaßnahme.

### Keine Registrierung im Core sichtbar

Enthält ein Mitschnitt auf der N2-Schnittstelle ausschließlich SCTP-Heartbeats,
aber keine `InitialUEMessage`, keinen Registration Request und keine SUCI oder
IMSI, hat der Registrierungsversuch Open5GS nicht erreicht. Dann zuerst die
Funk- und Mobilfunkeinstellungen des Endgeräts prüfen, insbesondere versteckte
oder herstellerspezifische Schalter für 5G. Ki, OPc und der Subscriber-Datensatz
sind zu diesem Zeitpunkt noch nicht beteiligt. Erst wenn NGAP-Nutzdaten sichtbar
sind, ist eine weitere Analyse im Core sinnvoll.
