# Backup und Wiederherstellung

## Umfang und Format

SIM-Admin erzeugt Dateien namens `sim-admin-backup-<datum>_<zeit>.sab`. Das
gesamte Paket ist mit AES-256-GCM verschlüsselt und enthält:

- Aktivitätsdatenbank,
- verschlüsselte Profildatenbank,
- zugehörigen Geräte-/Profiltresorschlüssel,
- Manifest mit SHA-256-Prüfsummen.

Der USB-Stick selbst muss dafür nicht vollständig verschlüsselt sein. Ohne das
mindestens zwölf Zeichen lange Backup-Passwort ist die `.sab`-Datei dennoch nicht
lesbar. Das Passwort wird weder in der Anwendung noch im Backup gespeichert.

## Backup erstellen

1. USB-Datenträger einstecken und warten, bis er eingebunden ist.
2. In SIM-Admin **Backup** öffnen.
3. Den erkannten Wechseldatenträger auswählen.
4. Ein eigenes Backup-Passwort zweimal eingeben.
5. **Verschlüsseltes Backup erstellen** wählen.
6. Die Erfolgsmeldung und Verifikation abwarten.
7. Den Datenträger über das Betriebssystem sicher auswerfen.

Nur tatsächlich eingebundene Datenträger unter den konfigurierten
Wechseldatenträgerpfaden werden akzeptiert. Eine frei eingegebene Pfadangabe ist
nicht möglich.

## Backup prüfen

1. USB-Datenträger einstecken und **Backup** öffnen.
2. Unter **Wiederherstellung** die `.sab`-Datei auswählen.
3. Backup-Passwort eingeben und **Backup prüfen** wählen.

Dabei werden Entschlüsselung, Formatversion, erlaubte Inhalte und alle
Prüfsummen kontrolliert. Die aktiven Daten werden noch nicht verändert.

## Wiederherstellen

Vorher möglichst ein zusätzliches aktuelles Backup erstellen. Danach:

1. Das gewünschte Backup wie oben beschrieben erfolgreich prüfen.
2. Die angezeigten Angaben zu Zeitpunkt und Inhalt kontrollieren.
3. **WIEDERHERSTELLEN** wählen und die Sicherheitsabfrage bestätigen.
4. Erfolgsmeldung abwarten.
5. Profiltresor und Aktivitätsprotokoll stichprobenartig kontrollieren.

Die Wiederherstellung ersetzt Aktivitätsdatenbank, Profiltresor und den dazu
gehörenden Profiltresorschlüssel durch den gesicherten Stand. Änderungen nach dem
Sicherungszeitpunkt gehen dadurch verloren. Eine Wiederherstellung mit falschem
Passwort, beschädigtem Paket oder inkompatibler Formatversion wird abgewiesen.

## Aufbewahrung

Mindestens zwei getrennte Datenträger verwenden und mehrere zeitlich getrennte
Backups behalten. Backup-Passwörter getrennt von den Datenträgern verwahren.
Inventar-CSV-Dateien sind redigierte Arbeitsunterlagen und keine
Wiederherstellungssicherung.

