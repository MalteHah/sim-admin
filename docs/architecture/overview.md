# Architekturübersicht

## Ziel

`sim-admin` wird als lokal betriebene, eigenständige Anwendung aufgebaut. Die
Fachlogik soll weder von FastAPI noch von pySim abhängen. Dadurch können
Kartenleser und weitere Provisionierungssysteme später über klar abgegrenzte
Adapter ergänzt werden.

## Schichten

```text
Weboberfläche / REST API
          |
    Anwendungsdienste
          |
      Fachmodelle
          |
 Adapter (pySim, PC/SC, SQLite, Backup und Export)
```

- `app/api`: Transportebene und Validierung von HTTP-Anfragen.
- `app/services`: Orchestrierung fachlicher Anwendungsfälle.
- `app/models`: Transport- und technikunabhängige Fachobjekte.
- `app/adapters`: Schnittstellen zu Geräten, Bibliotheken und Speichern.
- `app/core`: Querschnittsfunktionen wie Konfiguration und Protokollierung.
- `app/frontend`: Platzhalter für die spätere lokale Weboberfläche.

## Aktivitätsprotokoll

Sicherheitsrelevante Vorgänge werden in einer lokalen SQLite-Datenbank
protokolliert. Ein Eintrag enthält ausschließlich Zeitpunkt, Benutzer,
Vorgangsart, Ergebnis und einen fest definierten Statushinweis. ICCID, IMSI,
MSISDN, ATR, Ki, OPc, ADM, Passwörter, Formularinhalte und IP-Adressen werden
nicht aufgenommen. Die Datenbankdatei wird mit Dateimodus `0600` angelegt.

## Datensicherung

Backups können ausschließlich auf aktuell eingebundene Datenträger unter
den freigegebenen Mount-Pfaden geschrieben werden. Das Format `.sab` enthält
ein mit AES-256-GCM verschlüsseltes ZIP-Paket. Der Schlüssel wird mit scrypt
aus einem mindestens zwölf Zeichen langen, nicht gespeicherten Passwort
abgeleitet. Das Manifest enthält Formatversion und SHA-256-Prüfsummen. Aktuell
wird ein konsistenter Snapshot des Aktivitätsprotokolls gesichert. Vor einer
Wiederherstellung werden Authentizität, Formatversion und Prüfsumme kontrolliert;
das Ersetzen erfolgt erst nach einer getrennten Sicherheitsbestätigung.

## Reader-Adapter

Die erste Hardwaregrenze ist als `ReaderAdapter` definiert. Der konkrete
`PcscReaderAdapter` verwendet PC/SC über `pyscard`, um vorhandene Leser und den
Kartenstatus zu ermitteln. Er liest noch keine SIM-Dateien und schreibt keine
Kartendaten. Der Endpunkt `GET /api/v1/readers` stellt die Erkennung bereit und
meldet Infrastrukturfehler mit HTTP-Status 503.

Der `PySimCardAdapter` startet pySim-Aufrufe in dessen eigener Python-Umgebung
und übernimmt ausschließlich validierte JSON-Ergebnisse. Der Webprozess
importiert pySim daher nicht direkt. Lese- und Schreiboperationen verwenden
getrennte Bridge-Skripte. Schreibaufträge übertragen Geheimwerte ausschließlich
über die Standardeingabe des kurzlebigen Prozesses, nie als Kommandozeilenwert.

Der `ProvisioningPreviewService` besitzt absichtlich keinen Hardware- oder
pySim-Adapter und kann technisch keine Karte verändern. Schlüsselwerte werden
validiert, aber niemals in einer API-Antwort zurückgegeben.

Ein davon getrennter `CardComparisonService` verwendet ausschließlich den
read-only SIM-Adapter. Der `ProfileWriteService` ist die einzige Orchestrierung
für Kartenänderungen: ICCID-Prüfung, ADM1, explizite Freigabe, Schreiben,
Zurücklesen und anschließender Revisions-Commit. Ki und OPc werden nur für
eindeutig erkannte SysmocomSJA5-Karten freigegeben.

## Fachmodelle

Die ersten internen Modelle liegen in `app/models` und bleiben unabhängig von
FastAPI, pySim und einer späteren Datenbank:

- `Reader`: Kartenleser, Verbindungsstatus und ATR.
- `SIMProfile`: ICCID, IMSI, MSISDN, ACC sowie optionale Zugangsdaten.
- `IMSProfile`: IMPI, IMPU, Domain und IMS Service Table.
- `FiveGSProfile`: SUCI-Parameter und öffentliche Schlüssel des Heimnetzes.

Geheime Werte werden mit Pydantics `SecretStr` gekapselt, damit sie nicht
versehentlich in Standarddarstellungen und Logs im Klartext erscheinen. Das
ersetzt noch keine spätere Verschlüsselung bei Speicherung oder Export.

## Aktuelle Abgrenzung

Der aktuelle Stand enthält weiterhin keine:

- pySim-Abhängigkeit,
- Schreiben von SIM-Inhalten,
- Persistenz von SIM- oder Provisionierungsdaten,
- Import-, Export- oder Backup-Logik,
- Benutzerverwaltung.

## Vorgesehene pySim-Integration

pySim wird später ausschließlich hinter einem Adapter angesprochen. Die übrige
Anwendung arbeitet mit eigenen Fachmodellen und kennt weder pySim-Kommandos noch
dessen interne Datenstrukturen. Hardwarezugriffe lassen sich dadurch isoliert
testen und bei Bedarf austauschen.

## Sicherheitsgrundsatz

Künftige Schlüssel- und Zugangsdaten wie Ki, OPc, ADM, PIN oder PUK dürfen
nicht protokolliert werden. Speicherung, Export und Backup dieser Werte müssen
vor ihrer Implementierung ein eigenes Sicherheitskonzept erhalten.

Der produktive Dienst verwendet HTTPS mit einem lokalen Zertifikat. Port 8000
nimmt keine Anmeldedaten oder API-Aufrufe mehr an, sondern leitet ausschließlich
auf HTTPS an Port 8443 weiter. Sitzungscookies sind im Produktivbetrieb als
`Secure`, `HttpOnly` und `SameSite=Strict` markiert.
