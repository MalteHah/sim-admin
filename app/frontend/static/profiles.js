const list = document.querySelector("#profile-list");
const summary = document.querySelector("#profile-summary");
const refresh = document.querySelector("#profile-refresh");
const previewPanel = document.querySelector("#profile-preview");
const sortSelect = document.querySelector("#profile-sort");
const searchInput = document.querySelector("#profile-search");
const statusSelect = document.querySelector("#profile-status");
let loadedProfiles = [];
const secretsDialog = document.querySelector("#secrets-dialog");
const secretsForm = document.querySelector("#secrets-form");
const secretsValues = document.querySelector("#secrets-values");
const secretsError = document.querySelector("#secrets-error");
const secretsPromptText = document.querySelector("#secrets-prompt-text");
const secretsPasswordLabel = document.querySelector("#secrets-password-label");
const secretsPasswordInput = document.querySelector("#reveal-password");
const secretsSubmit = document.querySelector("#secrets-submit");
let revealProfileId = null;
let concealTimer = null;
const historyDialog = document.querySelector("#history-dialog");
const historyValues = document.querySelector("#history-values");
const changeDialog = document.querySelector("#change-dialog");
const changeForm = document.querySelector("#change-form");
const changeError = document.querySelector("#change-error");
const changeStatus = document.querySelector("#change-status");
const changeDiscard = document.querySelector("#change-discard");
const changePreview = document.querySelector("#change-preview");
const changeCompare = document.querySelector("#change-compare");
const changeWrite = document.querySelector("#change-write");
const writeConfirmationLabel = document.querySelector("#write-confirmation-label");
let changeProfileId = null;
const deleteDialog = document.querySelector("#delete-dialog");
const deleteForm = document.querySelector("#delete-form");
const deleteError = document.querySelector("#delete-error");
let deleteProfileId = null;
let deleteExpectedIccid = null;
const adoptDialog = document.querySelector("#adopt-dialog");
const adoptForm = document.querySelector("#adopt-form");
const adoptError = document.querySelector("#adopt-error");
let adoptProfileId = null;
const inventoryDialog = document.querySelector("#inventory-dialog");
const inventoryForm = document.querySelector("#inventory-form");
const inventoryStatus = document.querySelector("#inventory-status");
const inventoryIssuedTo = document.querySelector("#inventory-issued-to");
const inventoryIssuedAt = document.querySelector("#inventory-issued-at");
const inventoryNote = document.querySelector("#inventory-note");
const inventoryError = document.querySelector("#inventory-error");
let inventoryProfileId = null;
let suciKeys = [];

async function loadSuciKeyProfiles() {
  const response = await fetch("/api/v1/settings/suci-keys", {cache: "no-store"}); if (!response.ok) return;
  suciKeys = (await response.json()).filter(key => key.active);
  const select = document.querySelector("#change-suci-key-profile");
  for (const key of suciKeys) { const option = document.createElement("option"); option.value = String(key.id); option.textContent = `${key.name} · Profile ${key.scheme === 1 ? "A" : "B"} · ID ${key.key_id}`; select.append(option); }
}

document.querySelector("#change-suci-key-profile").addEventListener("change", (event) => {
  const key = suciKeys.find(item => item.id === Number(event.target.value));
  if (!key) { syncChangeSuciFields(); return; }
  document.querySelector("#change-protection-scheme").value = String(key.scheme);
  document.querySelector("#change-hn-public-key-id").value = String(key.key_id);
  document.querySelector("#change-hn-public-key").value = key.public_key;
  if (!document.querySelector("#change-routing-indicator").value) document.querySelector("#change-routing-indicator").value = "0000";
  syncChangeSuciFields();
});
document.querySelector("#change-protection-scheme").addEventListener("change", () => syncChangeSuciFields(true));

function syncChangeSuciFields(schemeChanged = false) {
  const profile = document.querySelector("#change-suci-key-profile");
  const scheme = document.querySelector("#change-protection-scheme");
  const keyId = document.querySelector("#change-hn-public-key-id");
  const publicKey = document.querySelector("#change-hn-public-key");
  if (schemeChanged && profile.value) {
    const selected = suciKeys.find(item => item.id === Number(profile.value));
    if (!selected || String(selected.scheme) !== scheme.value) profile.value = "";
  }
  if (scheme.value === "0" || scheme.value === "") {
    profile.value = ""; keyId.value = ""; publicKey.value = "";
    keyId.disabled = true; publicKey.disabled = true; profile.disabled = scheme.value === "0";
  } else {
    profile.disabled = false; keyId.disabled = false; publicKey.disabled = false;
    const catalogSelected = Boolean(profile.value);
    keyId.readOnly = catalogSelected; publicKey.readOnly = catalogSelected;
  }
}
loadSuciKeyProfiles();

function cell(value, className = "") {
  const element = document.createElement("td");
  element.textContent = value;
  element.className = className;
  return element;
}

const paginator = window.createTablePaginator(document.querySelector("#profile-pagination"), (profiles) => {
  list.replaceChildren();
  if (!profiles.length) {
    const emptyText = searchInput.value.trim() ? "Keine passenden Profile gefunden." : "Noch keine Profile gespeichert.";
    const row = document.createElement("tr"); row.className = "profile-message-row"; const empty = cell(emptyText); empty.colSpan = 9;
    row.append(empty); list.append(row); return;
  }
  for (const profile of profiles) {
    const row = document.createElement("tr");
    const actions = document.createElement("td");
    const previewButton = document.createElement("button"); previewButton.type = "button"; previewButton.textContent = "Dry Run";
    const compareButton = document.createElement("button"); compareButton.type = "button"; compareButton.textContent = profile.card_verified ? "Karte abgleichen" : "Karte zuordnen";
    const revealButton = document.createElement("button"); revealButton.type = "button"; revealButton.textContent = "Geheimnisse anzeigen";
    const historyButton = document.createElement("button"); historyButton.type = "button"; historyButton.textContent = "Historie";
    const changeButton = document.createElement("button"); changeButton.type = "button"; changeButton.textContent = profile.pending_change ? "Entwurf verwalten" : "Änderung vorbereiten";
    const deleteButton = document.createElement("button"); deleteButton.type = "button"; deleteButton.textContent = "Profil löschen"; deleteButton.className = "danger-button";
    const inventoryButton = document.createElement("button"); inventoryButton.type = "button"; inventoryButton.textContent = "Verwaltung";
    previewButton.addEventListener("click", () => previewProfile(profile.id));
    compareButton.addEventListener("click", () => compareProfile(profile));
    revealButton.addEventListener("click", () => openSecrets(profile.id));
    historyButton.addEventListener("click", () => showHistory(profile.id));
    changeButton.addEventListener("click", () => openChange(profile.id));
    deleteButton.addEventListener("click", () => openDelete(profile.id, profile.iccid));
    inventoryButton.addEventListener("click", () => openInventory(profile));
    actions.className = "table-actions"; actions.append(inventoryButton, previewButton, compareButton, revealButton, historyButton, changeButton, deleteButton);
    const iccidCell = cell(profile.iccid); const revision = document.createElement("small"); revision.className = "revision-badge"; revision.textContent = `Revision ${profile.revision}`; iccidCell.append(revision);
    const cardState = document.createElement("small"); cardState.className = profile.card_verified ? "card-verified-badge" : "card-pending-badge"; cardState.textContent = profile.card_verified ? "Karte geprüft" : "Kartenabgleich ausstehend"; iccidCell.append(cardState);
    if (profile.pending_change) { const pending = document.createElement("small"); pending.className = "pending-badge"; pending.textContent = "Änderung vorgemerkt"; iccidCell.append(pending); }
    const inventoryCell = cell(profile.inventory_status === "issued" ? "Ausgegeben" : "Im Bestand", profile.inventory_status === "issued" ? "inventory-issued" : "activity-ok");
    if (profile.inventory_status === "issued") { const details = document.createElement("small"); details.className = "inventory-details"; details.textContent = `${profile.issued_to} · ${new Date(`${profile.issued_at}T00:00:00`).toLocaleDateString("de-DE")}`; inventoryCell.append(details); }
    if (profile.inventory_note) { const note = document.createElement("small"); note.className = "inventory-details"; note.textContent = profile.inventory_note; note.title = profile.inventory_note; inventoryCell.append(note); }
    row.append(cell(new Date(profile.created_at).toLocaleString("de-DE")), iccidCell, cell(profile.imsi), inventoryCell,
      cell(profile.ims_configured ? "Vorhanden" : "Nicht gesetzt", profile.ims_configured ? "activity-ok" : ""),
      cell(profile.ki_configured ? "Vorhanden" : "Fehlt", profile.ki_configured ? "activity-ok" : "activity-error"),
      cell(profile.opc_configured ? "Vorhanden" : "Fehlt", profile.opc_configured ? "activity-ok" : "activity-error"),
      cell(profile.adm_configured ? "Vorhanden" : "Fehlt", profile.adm_configured ? "activity-ok" : "activity-error"), actions);
    list.append(row);
  }
});

async function loadProfiles() {
  refresh.disabled = true;
  try {
    const response = await fetch("/api/v1/profiles");
    if (!response.ok) throw new Error("Profiltresor konnte nicht geöffnet werden");
    loadedProfiles = await response.json();
    summary.textContent = `${loadedProfiles.length} verschlüsselt gespeicherte Profile`;
    applySorting();
  } catch (error) {
    summary.textContent = error.message;
    const row = document.createElement("tr"); row.className = "profile-message-row"; const errorCell = cell(error.message, "activity-error"); errorCell.colSpan = 9;
    row.append(errorCell); list.replaceChildren(row);
  } finally { refresh.disabled = false; }
}

function concealSecrets() {
  clearTimeout(concealTimer); concealTimer = null; revealProfileId = null;
  secretsValues.replaceChildren(); secretsValues.hidden = true; secretsError.hidden = true;
  secretsPasswordInput.value = ""; secretsPasswordInput.hidden = false; secretsPasswordInput.required = true;
  secretsPasswordLabel.hidden = false; secretsPromptText.hidden = false; secretsSubmit.hidden = false;
}

function openSecrets(id) { concealSecrets(); revealProfileId = id; secretsDialog.showModal(); secretsPasswordInput.focus(); }
document.querySelector("#secrets-close").addEventListener("click", () => { concealSecrets(); secretsDialog.close(); });
secretsDialog.addEventListener("close", concealSecrets);
secretsForm.addEventListener("submit", async (event) => {
  event.preventDefault(); secretsError.hidden = true;
  const response = await fetch(`/api/v1/profiles/${revealProfileId}/secrets`, {method: "POST", headers: {"Content-Type": "application/json", "Cache-Control": "no-store"}, body: JSON.stringify({password: secretsPasswordInput.value}), cache: "no-store"});
  const data = await response.json(); secretsPasswordInput.value = "";
  if (!response.ok) { secretsError.textContent = data.detail || "Freigabe fehlgeschlagen."; secretsError.hidden = false; return; }
  secretsValues.replaceChildren();
  for (const [name, value] of Object.entries(data.fields)) { const row = document.createElement("div"); const label = document.createElement("span"); const secret = document.createElement("code"); label.textContent = name; secret.textContent = value; row.append(label, secret); secretsValues.append(row); }
  secretsValues.hidden = false; secretsPasswordInput.hidden = true; secretsPasswordInput.required = false;
  secretsPasswordLabel.hidden = true; secretsPromptText.hidden = true; secretsSubmit.hidden = true;
  concealTimer = setTimeout(() => { concealSecrets(); secretsDialog.close(); }, 30000);
});

refresh.addEventListener("click", loadProfiles);
sortSelect.addEventListener("change", applySorting);
statusSelect.addEventListener("change", applySorting);
searchInput.addEventListener("input", applySorting);
loadProfiles();

function applySorting() {
  const [field, direction] = sortSelect.value.split("-");
  const query = searchInput.value.trim();
  const status = statusSelect.value;
  const filtered = loadedProfiles.filter((profile) => {
    const queryMatches = !query || profile.iccid.includes(query) || profile.imsi.includes(query);
    const statusMatches = status === "all" || (status === "verified" && profile.card_verified) ||
      (status === "pending-card" && !profile.card_verified) || (status === "pending-change" && profile.pending_change) ||
      (status === "in-stock" && profile.inventory_status === "in_stock") || (status === "issued" && profile.inventory_status === "issued");
    return queryMatches && statusMatches;
  });
  const sorted = [...filtered].sort((left, right) => left[field].localeCompare(right[field], "de", {numeric: true}));
  if (direction === "desc") sorted.reverse();
  summary.textContent = query || status !== "all" ? `${filtered.length} von ${loadedProfiles.length} Profilen gefunden` : `${loadedProfiles.length} verschlüsselt gespeicherte Profile`;
  paginator.setItems(sorted);
}

async function previewProfile(id) {
  previewPanel.hidden = false; previewPanel.textContent = "Dry Run wird erstellt …";
  const response = await fetch(`/api/v1/profiles/${id}/preview`, {method: "POST"});
  const data = await response.json();
  if (!response.ok) { previewPanel.textContent = data.detail || "Dry Run fehlgeschlagen."; return; }
  previewPanel.replaceChildren();
  const title = document.createElement("h2"); title.textContent = "Dry Run – kein Schreibzugriff";
  const text = document.createElement("p"); text.textContent = `${data.steps.length} geplante Schritte · Ki, OPc und ADM vorhanden · write_performed: false`;
  previewPanel.append(title, text);
}

async function compareProfile(profile) {
  previewPanel.hidden = false; previewPanel.textContent = "Karte wird ausschließlich gelesen …";
  const response = await fetch(`/api/v1/profiles/${profile.id}/card-comparison`, {method: "POST"});
  const data = await response.json();
  if (!response.ok) { previewPanel.textContent = data.detail?.message || "Kartenabgleich fehlgeschlagen."; return; }
  previewPanel.replaceChildren();
  const title = document.createElement("h2"); title.textContent = !profile.card_verified && data.iccid_matches ? "Karte zugeordnet – nur lesen" : "Kartenabgleich – nur lesen";
  const text = document.createElement("p");
  if (data.iccid_matches && data.imsi_matches) text.textContent = "ICCID und IMSI stimmen mit dem Tresorprofil überein.";
  else if (data.iccid_matches) text.textContent = "Die ICCID wurde sicher zugeordnet. Die IMSI der Karte weicht vom Tresorprofil ab.";
  else text.textContent = "Die ICCID stimmt nicht überein. Die Karte wurde diesem Profil nicht zugeordnet.";
  previewPanel.append(title, text);
  appendSuciComparison(previewPanel, data);
  if (data.iccid_matches && !data.imsi_matches) {
    const adoptButton = document.createElement("button");
    adoptButton.type = "button"; adoptButton.textContent = "IMSI der Karte übernehmen";
    adoptButton.addEventListener("click", () => {
      adoptProfileId = profile.id; adoptForm.reset(); adoptError.hidden = true; adoptDialog.showModal();
      document.querySelector("#adopt-password").focus();
    });
    previewPanel.append(adoptButton);
  }
  if (data.iccid_matches) await loadProfiles();
}

function appendSuciComparison(container, data) {
  if (!data.suci_compared) return;
  const heading = document.createElement("h3"); heading.textContent = "SUCI-Konfiguration";
  const text = document.createElement("p");
  if (!data.suci_readable) text.textContent = "Die SUCI-Daten konnten auf dieser Karte nicht gelesen werden.";
  else text.textContent = data.suci_matches
    ? "Routing Indicator, Schutzverfahren, HN-Schlüssel und UST-Dienste stimmen mit dem Tresorprofil überein."
    : "Die SUCI-Konfiguration weicht vom Tresorprofil ab.";
  container.append(heading, text);
  if (!data.suci_readable) return;
  const details = document.createElement("p");
  const schemes = {0: "Null Scheme", 1: "Profile A – X25519", 2: "Profile B – P-256"};
  details.textContent = `Karte: Routing Indicator ${data.current_routing_indicator || "–"} · ${schemes[data.current_protection_scheme] || "Unbekannt"} · HN-Key-ID ${data.current_hn_public_key_id ?? "–"} · öffentlicher Schlüssel ${data.hn_public_key_matches ? "stimmt überein" : "abweichend"} · UST 124 ${data.suci_service_124_active ? "aktiv" : "inaktiv"} · UST 125 ${data.suci_service_125_active ? "aktiv" : "inaktiv"}`;
  container.append(details);
}

document.querySelector("#adopt-close").addEventListener("click", () => adoptDialog.close());
adoptDialog.addEventListener("close", () => { adoptForm.reset(); adoptError.hidden = true; adoptProfileId = null; });
adoptForm.addEventListener("submit", async (event) => {
  event.preventDefault(); adoptError.hidden = true;
  const submit = adoptForm.querySelector('button[type="submit"]'); submit.disabled = true;
  try {
    const response = await fetch(`/api/v1/profiles/${adoptProfileId}/adopt-card`, {
      method: "POST", headers: {"Content-Type": "application/json", "Cache-Control": "no-store"},
      body: JSON.stringify({password: document.querySelector("#adopt-password").value, reader_index: 0}), cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) {
      adoptError.textContent = data.detail?.message || data.detail || "Kartendaten konnten nicht übernommen werden.";
      adoptError.hidden = false; return;
    }
    adoptDialog.close(); previewPanel.hidden = false; previewPanel.replaceChildren();
    const title = document.createElement("h2"); title.textContent = "IMSI der Karte übernommen";
    const text = document.createElement("p"); text.textContent = `Die IMSI wurde als Revision ${data.revision} im Profiltresor gespeichert. Auf die SIM-Karte wurde nichts geschrieben.`;
    previewPanel.append(title, text); await loadProfiles();
  } finally { submit.disabled = false; document.querySelector("#adopt-password").value = ""; }
});

async function showHistory(id) {
  historyValues.textContent = "Historie wird geladen …"; historyDialog.showModal();
  const response = await fetch(`/api/v1/profiles/${id}/revisions`);
  const revisions = await response.json();
  if (!response.ok) { historyValues.textContent = revisions.detail || "Historie konnte nicht geladen werden."; return; }
  historyValues.replaceChildren();
  for (const item of revisions) {
    const row = document.createElement("div"); const revision = document.createElement("strong"); const time = document.createElement("span");
    revision.textContent = `Revision ${item.revision}`; time.textContent = new Date(item.created_at).toLocaleString("de-DE");
    row.append(revision, time); historyValues.append(row);
  }
}

document.querySelector("#history-close").addEventListener("click", () => historyDialog.close());

async function openChange(id) {
  changeProfileId = id; changeError.hidden = true; changeStatus.hidden = true; changeDiscard.hidden = true; changePreview.hidden = true; changeCompare.hidden = true; changeWrite.hidden = true; writeConfirmationLabel.hidden = true; changeForm.reset();
  const [response, draftResponse] = await Promise.all([fetch(`/api/v1/profiles/${id}/editable`, {cache: "no-store"}), fetch(`/api/v1/profiles/${id}/change-draft`, {cache: "no-store"})]);
  const profile = await response.json();
  if (!response.ok) { previewPanel.hidden = false; previewPanel.textContent = profile.detail || "Profil konnte nicht geladen werden."; return; }
  document.querySelector("#change-iccid").value = profile.iccid;
  document.querySelector("#change-revision").value = `Revision ${profile.revision}`;
  document.querySelector("#change-imsi").value = profile.imsi;
  document.querySelector("#change-msisdn").value = profile.msisdn || "";
  document.querySelector("#change-acc").value = profile.acc;
  document.querySelector("#change-impi").value = profile.impi || "";
  document.querySelector("#change-impu").value = profile.impu || "";
  document.querySelector("#change-ims-domain").value = profile.ims_domain || "";
  document.querySelector("#change-ist").value = profile.ist || "";
  document.querySelector("#change-routing-indicator").value = profile.routing_indicator || "";
  document.querySelector("#change-protection-scheme").value = profile.protection_scheme ?? "";
  document.querySelector("#change-hn-public-key-id").value = profile.hn_public_key_id ?? "";
  document.querySelector("#change-hn-public-key").value = profile.hn_public_key || "";
  syncChangeSuciFields();
  if (draftResponse.ok) {
    const draft = await draftResponse.json();
    if (draft) { changeStatus.textContent = `Vorgemerkt seit ${new Date(draft.created_at).toLocaleString("de-DE")}: ${draft.changed_fields.join(", ").toUpperCase()}. Aktive Revision: ${draft.base_revision}.`; changeStatus.hidden = false; changeDiscard.hidden = false; changePreview.hidden = false; changeCompare.hidden = false; changeWrite.hidden = false; }
  }
  changeDialog.showModal(); document.querySelector("#change-imsi").focus();
}

document.querySelector("#change-close").addEventListener("click", () => changeDialog.close());
changeDialog.addEventListener("close", () => { changeForm.reset(); changeError.hidden = true; changeProfileId = null; });
changeForm.addEventListener("submit", async (event) => {
  event.preventDefault(); changeError.hidden = true;
  const submit = changeForm.querySelector('button[type="submit"]'); submit.disabled = true;
  const payload = {
    imsi: document.querySelector("#change-imsi").value,
    msisdn: document.querySelector("#change-msisdn").value || null,
    acc: document.querySelector("#change-acc").value,
    ki: document.querySelector("#change-ki").value || null,
    opc: document.querySelector("#change-opc").value || null,
    impi: document.querySelector("#change-impi").value || null,
    impu: document.querySelector("#change-impu").value || null,
    ims_domain: document.querySelector("#change-ims-domain").value || null,
    ist: document.querySelector("#change-ist").value || null,
    routing_indicator: document.querySelector("#change-routing-indicator").value || null,
    protection_scheme: document.querySelector("#change-protection-scheme").value === "" ? null : Number(document.querySelector("#change-protection-scheme").value),
    hn_public_key_id: document.querySelector("#change-hn-public-key-id").value === "" ? null : Number(document.querySelector("#change-hn-public-key-id").value),
    hn_public_key: document.querySelector("#change-hn-public-key").value || null,
    password: document.querySelector("#change-password").value,
  };
  try {
    const response = await fetch(`/api/v1/profiles/${changeProfileId}/change-draft`, {method: "POST", headers: {"Content-Type": "application/json", "Cache-Control": "no-store"}, body: JSON.stringify(payload), cache: "no-store"});
    const data = await response.json();
    if (!response.ok) { changeError.textContent = typeof data.detail === "string" ? data.detail : "Entwurf konnte nicht gespeichert werden."; changeError.hidden = false; return; }
    changeDialog.close(); previewPanel.hidden = false; previewPanel.replaceChildren();
    const title = document.createElement("h2"); title.textContent = "Änderungsentwurf gespeichert";
    const text = document.createElement("p"); text.textContent = `Vorgemerkt: ${data.changed_fields.join(", ").toUpperCase()}. Das aktive Profil bleibt auf Revision ${data.base_revision}; es wurde nichts auf die SIM geschrieben.`;
    previewPanel.append(title, text); await loadProfiles();
  } finally { submit.disabled = false; document.querySelector("#change-password").value = ""; }
});

changeDiscard.addEventListener("click", async () => {
  changeError.hidden = true;
  const password = document.querySelector("#change-password").value;
  if (!password) { changeError.textContent = "Zum Verwerfen ist das aktuelle Anmeldepasswort erforderlich."; changeError.hidden = false; return; }
  if (!window.confirm("Diesen Änderungsentwurf wirklich verwerfen? Das aktive Profil bleibt unverändert.")) return;
  changeDiscard.disabled = true;
  try {
    const response = await fetch(`/api/v1/profiles/${changeProfileId}/change-draft/discard`, {method: "POST", headers: {"Content-Type": "application/json", "Cache-Control": "no-store"}, body: JSON.stringify({password}), cache: "no-store"});
    if (!response.ok) { const data = await response.json(); changeError.textContent = data.detail || "Entwurf konnte nicht verworfen werden."; changeError.hidden = false; return; }
    changeDialog.close(); previewPanel.hidden = false; previewPanel.replaceChildren();
    const title = document.createElement("h2"); title.textContent = "Änderungsentwurf verworfen";
    const text = document.createElement("p"); text.textContent = "Das aktive Profil und seine Revision sind unverändert geblieben.";
    previewPanel.append(title, text); await loadProfiles();
  } finally { changeDiscard.disabled = false; document.querySelector("#change-password").value = ""; }
});

changePreview.addEventListener("click", async () => {
  changePreview.disabled = true; changeError.hidden = true;
  try {
    const response = await fetch(`/api/v1/profiles/${changeProfileId}/change-draft/preview`, {method: "POST", cache: "no-store"});
    const data = await response.json();
    if (!response.ok) { changeError.textContent = data.detail || "Entwurf konnte nicht geprüft werden."; changeError.hidden = false; return; }
    changeDialog.close(); previewPanel.hidden = false; previewPanel.replaceChildren();
    const title = document.createElement("h2"); title.textContent = "Entwurfsprüfung – kein Schreibzugriff";
    const text = document.createElement("p"); text.textContent = `${data.steps.length} geplante Schritte geprüft. Geheimwerte sind vorhanden und verdeckt; write_performed: false.`;
    previewPanel.append(title, text);
    appendSuciComparison(previewPanel, data);
  } finally { changePreview.disabled = false; }
});

changeCompare.addEventListener("click", async () => {
  changeCompare.disabled = true; changeError.hidden = true;
  try {
    const response = await fetch(`/api/v1/profiles/${changeProfileId}/change-draft/card-comparison`, {method: "POST", cache: "no-store"});
    const data = await response.json();
    if (!response.ok) { changeError.textContent = data.detail?.message || data.detail || "Kartenabgleich fehlgeschlagen."; changeError.hidden = false; return; }
    changeDialog.close(); previewPanel.hidden = false; previewPanel.replaceChildren();
    const title = document.createElement("h2"); title.textContent = "Entwurf gegen Karte – nur lesen";
    const text = document.createElement("p");
    if (data.iccid_matches && data.imsi_matches) text.textContent = "ICCID und IMSI der Karte entsprechen dem vorgemerkten Zielzustand. Es wurde nichts geschrieben.";
    else if (data.iccid_matches) text.textContent = "Die ICCID gehört zum Profil; die IMSI unterscheidet sich vom vorgemerkten Zielzustand. Das ist vor dem Schreiben eines IMSI-Entwurfs erwartbar.";
    else text.textContent = "Die ICCID der eingelegten Karte gehört nicht zu diesem Profil. Ein späterer Schreibvorgang darf so nicht freigegeben werden.";
    previewPanel.append(title, text);
    if (data.iccid_matches) await loadProfiles();
  } finally { changeCompare.disabled = false; }
});

changeWrite.addEventListener("click", async () => {
  changeError.hidden = true;
  if (writeConfirmationLabel.hidden) {
    writeConfirmationLabel.hidden = false;
    changeError.textContent = "Für den tatsächlichen Schreibvorgang jetzt das aktuelle Passwort und SIM SCHREIBEN eingeben.";
    changeError.hidden = false;
    document.querySelector("#write-confirmation").focus();
    return;
  }
  const password = document.querySelector("#change-password").value;
  const confirmation = document.querySelector("#write-confirmation").value;
  if (!password || confirmation !== "SIM SCHREIBEN") { changeError.textContent = "Passwort und die exakte Schreibfreigabe SIM SCHREIBEN sind erforderlich."; changeError.hidden = false; return; }
  if (!window.confirm("Jetzt tatsächlich auf die eingelegte SIM schreiben? Der Vorgang darf nicht unterbrochen werden.")) return;
  changeWrite.disabled = true;
  try {
    const response = await fetch(`/api/v1/profiles/${changeProfileId}/change-draft/write`, {method: "POST", headers: {"Content-Type": "application/json", "Cache-Control": "no-store"}, body: JSON.stringify({password, confirmation, reader_index: 0}), cache: "no-store"});
    const data = await response.json();
    if (!response.ok) { changeError.textContent = data.detail?.message || data.detail || "SIM-Schreibvorgang fehlgeschlagen."; changeError.hidden = false; return; }
    changeDialog.close(); previewPanel.hidden = false; previewPanel.replaceChildren();
    const title = document.createElement("h2"); title.textContent = "SIM erfolgreich geschrieben und geprüft";
    const text = document.createElement("p"); text.textContent = `Bestätigt: ${data.verified_fields.join(", ").toUpperCase()}. Das Profil ist jetzt Revision ${data.revision}.`;
    previewPanel.append(title, text); await loadProfiles();
  } finally { changeWrite.disabled = false; document.querySelector("#change-password").value = ""; document.querySelector("#write-confirmation").value = ""; }
});

function updateInventoryFields() {
  const issued = inventoryStatus.value === "issued";
  document.querySelector("#inventory-issued-to-label").hidden = !issued;
  document.querySelector("#inventory-issued-at-label").hidden = !issued;
  inventoryIssuedTo.required = issued; inventoryIssuedAt.required = issued;
  if (!issued) { inventoryIssuedTo.value = ""; inventoryIssuedAt.value = ""; }
}

function openInventory(profile) {
  inventoryProfileId = profile.id; inventoryForm.reset(); inventoryError.hidden = true;
  inventoryStatus.value = profile.inventory_status || "in_stock";
  inventoryIssuedTo.value = profile.issued_to || "";
  inventoryIssuedAt.value = profile.issued_at || new Date().toISOString().slice(0, 10);
  inventoryNote.value = profile.inventory_note || "";
  document.querySelector("#inventory-note-count").textContent = `${inventoryNote.value.length} / 500`;
  updateInventoryFields(); inventoryDialog.showModal(); inventoryStatus.focus();
}

inventoryStatus.addEventListener("change", updateInventoryFields);
inventoryNote.addEventListener("input", () => { document.querySelector("#inventory-note-count").textContent = `${inventoryNote.value.length} / 500`; });
document.querySelector("#inventory-close").addEventListener("click", () => inventoryDialog.close());
inventoryDialog.addEventListener("close", () => { inventoryForm.reset(); inventoryProfileId = null; inventoryError.hidden = true; });
inventoryForm.addEventListener("submit", async (event) => {
  event.preventDefault(); inventoryError.hidden = true;
  const submit = inventoryForm.querySelector('button[type="submit"]'); submit.disabled = true;
  const issued = inventoryStatus.value === "issued";
  const payload = {status: inventoryStatus.value, issued_to: issued ? inventoryIssuedTo.value : null,
    issued_at: issued ? inventoryIssuedAt.value : null, note: inventoryNote.value || null,
    password: document.querySelector("#inventory-password").value};
  try {
    const response = await fetch(`/api/v1/profiles/${inventoryProfileId}/inventory`, {method: "POST", headers: {"Content-Type": "application/json", "Cache-Control": "no-store"}, body: JSON.stringify(payload), cache: "no-store"});
    const data = await response.json();
    if (!response.ok) { inventoryError.textContent = typeof data.detail === "string" ? data.detail : "Verwaltungsdaten konnten nicht gespeichert werden."; inventoryError.hidden = false; return; }
    inventoryDialog.close(); previewPanel.hidden = false; previewPanel.replaceChildren();
    const title = document.createElement("h2"); title.textContent = data.inventory_status === "issued" ? "Karte als ausgegeben markiert" : "Karte im Bestand";
    const text = document.createElement("p"); text.textContent = "Nur die Verwaltungsdaten wurden geändert. SIM-Profil und Revision bleiben unverändert.";
    previewPanel.append(title, text); await loadProfiles();
  } catch (error) {
    inventoryError.textContent = "Verwaltungsdaten konnten nicht gespeichert werden. Bitte Verbindung prüfen und erneut versuchen.";
    inventoryError.hidden = false;
  } finally { submit.disabled = false; document.querySelector("#inventory-password").value = ""; }
});

function openDelete(id, iccid) {
  deleteForm.reset(); deleteError.hidden = true; deleteProfileId = id; deleteExpectedIccid = iccid; deleteDialog.showModal(); document.querySelector("#delete-iccid").focus();
}

document.querySelector("#delete-close").addEventListener("click", () => deleteDialog.close());
deleteDialog.addEventListener("close", () => { deleteForm.reset(); deleteError.hidden = true; deleteProfileId = null; deleteExpectedIccid = null; });
deleteForm.addEventListener("submit", async (event) => {
  event.preventDefault(); deleteError.hidden = true;
  const iccid = document.querySelector("#delete-iccid").value;
  const password = document.querySelector("#delete-password").value;
  if (iccid !== deleteExpectedIccid) { deleteError.textContent = "Die eingegebene ICCID stimmt nicht mit dem Profil überein."; deleteError.hidden = false; return; }
  if (!window.confirm("Profil einschließlich aller Revisionen jetzt endgültig löschen?")) return;
  const submit = deleteForm.querySelector('button[type="submit"]'); submit.disabled = true;
  try {
    const response = await fetch(`/api/v1/profiles/${deleteProfileId}/delete`, {method: "POST", headers: {"Content-Type": "application/json", "Cache-Control": "no-store"}, body: JSON.stringify({password, confirmation_iccid: iccid}), cache: "no-store"});
    if (!response.ok) { const data = await response.json(); deleteError.textContent = data.detail || "Profil konnte nicht gelöscht werden."; deleteError.hidden = false; return; }
    deleteDialog.close(); previewPanel.hidden = false; previewPanel.replaceChildren();
    const title = document.createElement("h2"); title.textContent = "Profil gelöscht";
    const text = document.createElement("p"); text.textContent = "Das Profil, seine Revisionen und ein möglicher Änderungsentwurf wurden entfernt.";
    previewPanel.append(title, text); await loadProfiles();
  } finally { submit.disabled = false; document.querySelector("#delete-password").value = ""; }
});
