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
abgeleitet. Das Manifest enthält Formatversion und SHA-256-Prüfsummen. Gesichert
werden konsistente Snapshots von Aktivitätsprotokoll und Profiltresor sowie der
zugehörige Tresorschlüssel. Damit sind Profile, Revisionen, Entwürfe,
Bestandsdaten, SPN und SUCI-Schlüsselkatalog enthalten. Vor einer
Wiederherstellung werden Authentizität, Formatversion und Prüfsummen kontrolliert;
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
Zurücklesen und anschließender Revisions-Commit. Ki, OPc, IMS- und
5GS-/SUCI-Felder werden nur für eindeutig erkannte SysmocomSJA5-Karten
freigegeben.

ADM1 ist ausschließlich ein Autorisierungsnachweis. Die Anwendung besitzt
keinen Pfad zum Lesen, Ändern, Entsperren, Zurücksetzen oder Schreiben von ADM1
auf der Karte; diese Grenze ist Teil des Sicherheitsmodells.

## Fachmodelle

Die ersten internen Modelle liegen in `app/models` und bleiben unabhängig von
FastAPI, pySim und einer späteren Datenbank:

- `Reader`: Kartenleser, Verbindungsstatus und ATR.
- `SIMProfile`: ICCID, IMSI, MSISDN, ACC sowie optionale Zugangsdaten.
- `IMSProfile`: IMPI, IMPU, Domain und IMS Service Table.
- `FiveGSProfile`: SUCI-Parameter und öffentliche Schlüssel des Heimnetzes.

Die IMS-Felder IMPI, IMPU, IMS-Domain und IST sind optional in den verschlüsselten
Profilrecords enthalten. Fehlende Schlüssel werden beim Lesen älterer Records als
„nicht gesetzt“ behandelt. Auf eindeutig erkannten SysmocomSJA5-Karten können sie
nach ICCID- und ADM1-Prüfung geschrieben und unmittelbar zurückgelesen werden.

Der Service Provider Name (SPN) ist ein optionales Feld mit höchstens 16
ASCII-Zeichen. Der Schreibadapter erhält das vorhandene Anzeige-Byte der Karte
und ersetzt ausschließlich den Namen. Vergleich und Übernahme unterscheiden
bewusst zwischen „nicht verwaltet“ und „abweichend“.

Routing Indicator, Protection Scheme, Home-Network Public Key ID und Public Key
sind ebenfalls optionale Bestandteile derselben verschlüsselten Profilrecords.
Für SJA5 stehen zwei SUCI-Berechnungsarten zur Verfügung. Die Berechnung im
Endgerät verwendet `DF.5GS/EF.Routing_Indicator`,
`DF.5GS/EF.SUCI_Calc_Info`, UST 124 aktiv und UST 125 inaktiv. Bis zu acht
Protection-Scheme-Einträge können mit eindeutigen Prioritäten verwaltet werden.
Auf S17 kann alternativ Profile B über `DF.SAIP` direkt auf der USIM berechnet
werden; dafür sind UST 124 und 125 gemeinsam aktiv und die Priorität ist 0. Der
Listenindex des Public Keys bleibt von der Open5GS-HN-Key-ID getrennt. Alle Ziele
werden vor der ersten Mutation gelesen; ein Revisions-Commit folgt erst nach
erfolgreichem Readback.

Geheime Werte werden mit Pydantics `SecretStr` gekapselt, damit sie nicht
versehentlich in Standarddarstellungen und Logs im Klartext erscheinen. Im
Profiltresor und in Änderungsentwürfen werden sie zusätzlich gerätegebunden mit
AES-256-GCM verschlüsselt gespeichert; Exporte bleiben grundsätzlich redigiert.

## Aktuelle Abgrenzung

Der aktuelle Stand unterstützt ausschließlich eindeutig erkannte und getestete
Kartenpfade. Weitere Hersteller und Kartentypen, eine Stapelverarbeitung sowie
die Wiederaufnahme unterbrochener Schreibvorgänge gehören zur Revision 2. ADM1
wird ausschließlich zur Schreibautorisierung geprüft und niemals gelesen,
geändert, entsperrt oder geschrieben.

## pySim-Integration

pySim wird ausschließlich hinter einem Adapter angesprochen. Die übrige
Anwendung arbeitet mit eigenen Fachmodellen und kennt weder pySim-Kommandos noch
dessen interne Datenstrukturen. Hardwarezugriffe lassen sich dadurch isoliert
testen und bei Bedarf austauschen.

## Sicherheitsgrundsatz

Schlüssel- und Zugangsdaten wie Ki, OPc, ADM, PIN oder PUK dürfen nicht
protokolliert werden. Sie werden im Profiltresor gerätegebunden verschlüsselt;
Exporte bleiben redigiert und USB-Backups werden zusätzlich mit einem separaten
Passwort vollständig verschlüsselt.

Der produktive Dienst verwendet HTTPS mit einem lokalen Zertifikat. Port 8000
nimmt keine Anmeldedaten oder API-Aufrufe mehr an, sondern leitet ausschließlich
auf HTTPS an Port 8443 weiter. Sitzungscookies sind im Produktivbetrieb als
`Secure`, `HttpOnly` und `SameSite=Strict` markiert.
