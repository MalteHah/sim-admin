const actionLabels = {
  "auth.login": "Anmeldung",
  "auth.logout": "Abmeldung",
  "auth.password_change": "Passwortänderung",
  "sim.read": "SIM gelesen",
  "provisioning.preview": "Dry Run",
  "provisioning.card_comparison": "Kartenabgleich",
  "backup.create": "Backup erstellt",
  "backup.inspect": "Backup geprüft",
  "backup.restore": "Backup wiederhergestellt",
  "import.csv_preview": "CSV-Import geprüft",
  "profiles.import": "Profile importiert",
  "profiles.preview": "Tresorprofil Dry Run",
  "profiles.card_comparison": "Tresorprofil Kartenabgleich",
  "profiles.reveal": "Profilgeheimnisse angezeigt",
  "profiles.inventory_export": "Profilinventar exportiert",
  "profiles.change_draft": "Änderungsentwurf gespeichert",
  "profiles.change_draft_discard": "Änderungsentwurf verworfen",
  "profiles.change_draft_preview": "Änderungsentwurf Dry Run",
  "profiles.change_draft_card_comparison": "Entwurf mit Karte abgeglichen",
  "profiles.change_draft_write": "Änderung auf SIM geschrieben",
  "profiles.single_create": "Einzelprofil gespeichert",
  "profiles.delete": "Profil gelöscht",
  "profiles.inventory_update": "Bestandsverwaltung geändert",
};

const detailLabels = {
  "dry-run": "Kein Schreibzugriff",
  match: "Identisch",
  difference: "Abweichung",
  invalid_credentials: "Anmeldung abgelehnt",
  invalid_password: "Aktuelles Passwort falsch",
  no_card: "Keine Karte",
  encrypted_verified: "Verschlüsselt und geprüft",
  invalid_target: "Datenträger nicht verfügbar",
  weak_password: "Backup-Passwort zu kurz",
  write_failed: "Schreibfehler",
  encrypted_pending: "Verschlüsselt vorgemerkt",
  discarded: "Entwurf entfernt",
  encrypted_revision_1: "Verschlüsselt als Revision 1",
  encrypted_revision_1_verified: "Revision 1, Karte geprüft",
  encrypted_revision_1_pending_card: "Revision 1, Kartenabgleich ausstehend",
  profile_revisions_and_draft: "Profil vollständig entfernt",
  reauthentication_failed: "Passwortbestätigung fehlgeschlagen",
  confirmation_mismatch: "Bestätigung stimmt nicht überein",
  duplicate_iccid: "ICCID bereits vorhanden",
  card_changed: "Karte wurde gewechselt",
  reauthenticated: "Passwort erneut bestätigt",
  protocol_error: "SIM-Karte antwortet nicht",
  reader_error: "Kartenleser nicht verfügbar",
  no_reader: "Kein Kartenleser verfügbar",
  read_failed: "Karte konnte nicht gelesen werden",
  write_failed: "Schreibvorgang fehlgeschlagen",
  verification_failed: "Rückprüfung fehlgeschlagen",
  adm_verification_failed: "ADM1 wurde abgelehnt",
  iccid_mismatch: "ICCID stimmt nicht überein",
  unsupported_card: "Kartentyp nicht unterstützt",
  unsupported_card_for_ims: "Kartentyp unterstützt diese Felder nicht",
  unsupported_card_for_auth_keys: "Kartentyp unterstützt Ki/OPc nicht",
  unsupported_fields: "Felder noch nicht unterstützt",
  missing_draft: "Änderungsentwurf fehlt",
  revision_conflict: "Profilrevision wurde zwischenzeitlich geändert",
  invalid_csv: "CSV-Datei nicht lesbar",
  missing_columns: "CSV-Pflichtspalten fehlen",
  unknown_columns: "CSV enthält unbekannte Spalten",
  validation_errors: "Validierungsfehler vorhanden",
  valid: "Datei vollständig gültig",
  encrypted: "Verschlüsselt gespeichert",
  redacted: "Ohne Geheimwerte exportiert",
  integrity_valid: "Integrität bestätigt",
  decryption_failed: "Passwort falsch oder Datei beschädigt",
  invalid_backup: "Backup ungültig",
  incompatible_backup: "Backupversion nicht kompatibel",
  inventory_in_stock: "Karte im Bestand",
  inventory_issued: "Karte ausgegeben",
};

function translateDetail(detail) {
  if (!detail) return "–";
  const revision = /^revision_(\d+)$/.exec(detail);
  if (revision) return `Als Revision ${revision[1]} übernommen`;
  return detailLabels[detail] || detail.replaceAll("_", " ");
}

const list = document.querySelector("#activity-list");
const refresh = document.querySelector("#activity-refresh");

function cell(value) {
  const element = document.createElement("td");
  element.textContent = value;
  return element;
}

const paginator = window.createTablePaginator(document.querySelector("#activity-pagination"), (events) => {
  list.replaceChildren();
  if (!events.length) {
    const row = document.createElement("tr"); const empty = cell("Noch keine Aktivitäten vorhanden."); empty.colSpan = 5;
    row.append(empty); list.append(row); return;
  }
  for (const event of events) {
    const row = document.createElement("tr");
    const status = event.status === "success" ? "Erfolgreich" : "Fehler";
    const statusCell = cell(status); statusCell.className = event.status === "success" ? "activity-ok" : "activity-error";
    row.append(cell(new Date(event.created_at).toLocaleString("de-DE")), cell(event.username), cell(actionLabels[event.action] || event.action), statusCell, cell(translateDetail(event.detail)));
    list.append(row);
  }
});

async function loadActivities() {
  refresh.disabled = true;
  try {
    const response = await fetch("/api/v1/audit?limit=500");
    if (!response.ok) throw new Error("Protokoll konnte nicht geladen werden");
    const events = await response.json();
    paginator.setItems(events);
  } catch (error) {
    list.innerHTML = "";
    const row = document.createElement("tr");
    const message = cell(error.message);
    message.colSpan = 5;
    message.className = "activity-error";
    row.append(message);
    list.append(row);
  } finally {
    refresh.disabled = false;
  }
}

refresh.addEventListener("click", loadActivities);
loadActivities();
