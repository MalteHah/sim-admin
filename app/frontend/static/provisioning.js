const form = document.querySelector("#provisioning-form");
const panel = document.querySelector("#preview-panel");
const errorMessage = document.querySelector("#preview-error");
const submitButton = form.querySelector("button[type='submit']");
const comparisonPanel = document.querySelector("#comparison-panel");
const readCardButton = document.querySelector("#read-single-card");
const cardStatus = document.querySelector("#single-card-status");
const saveButton = document.querySelector("#save-single-profile");
let comparisonTarget = null;
let unknownCard = false;
let dryRunReady = false;
let captureMode = "card";

for (const option of document.querySelectorAll('input[name="capture-mode"]')) option.addEventListener("change", () => {
  captureMode = option.value; unknownCard = captureMode === "data"; dryRunReady = false; saveButton.disabled = true;
  form.iccid.value = ""; form.imsi.value = ""; form.iccid.readOnly = captureMode === "card"; form.imsi.readOnly = captureMode === "card";
  readCardButton.hidden = captureMode !== "card";
  document.querySelector("#iccid-label").textContent = captureMode === "card" ? "ICCID – von Karte" : "ICCID – aus Datensatz";
  document.querySelector("#imsi-label").textContent = captureMode === "card" ? "IMSI – von Karte" : "IMSI – aus Datensatz";
  cardStatus.hidden = false;
  cardStatus.textContent = captureMode === "card" ? "Lege die passende Karte ein und lies sie ein." : "Der Datensatz wird als „Kartenabgleich ausstehend“ gespeichert. Vor einem Schreibzugriff muss später die passende ICCID gelesen werden.";
});

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}

function optionalNumber(values, name) {
  const value = values.get(name);
  return value === "" ? null : Number(value);
}

function profileFields(values) {
  return {
    iccid: values.get("iccid"), imsi: values.get("imsi"), msisdn: values.get("msisdn") || null,
    acc: values.get("acc"), ki: values.get("ki"), opc: values.get("opc"), adm: values.get("adm"),
    impi: values.get("impi") || null, impu: values.get("impu") || null,
    ims_domain: values.get("ims_domain") || null, ist: values.get("ist") || null,
    routing_indicator: values.get("routing_indicator") || null,
    protection_scheme: optionalNumber(values, "protection_scheme"),
    hn_public_key_id: optionalNumber(values, "hn_public_key_id"),
    hn_public_key: values.get("hn_public_key") || null,
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const values = new FormData(form);
    const response = await fetch("/api/v1/provisioning/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profileFields(values)),
    });
    const preview = await response.json();
    if (!response.ok) throw new Error("Eingaben sind unvollständig oder ungültig.");
    panel.innerHTML = `
      <p class="eyebrow">Vorschau · Kein Schreibzugriff</p>
      <h2>${escapeHtml(preview.iccid)}</h2>
      <dl class="preview-summary">
        <div><dt>IMSI</dt><dd>${escapeHtml(preview.imsi)}</dd></div>
        <div><dt>ACC</dt><dd>${escapeHtml(preview.acc)}</dd></div>
        <div><dt>Schlüssel</dt><dd>Ki, OPc und ADM gesetzt</dd></div>
      </dl>
      <ol class="preview-steps">
        ${preview.steps.map((step) => `
          <li><strong>${escapeHtml(step.action)}</strong><span>${escapeHtml(step.target)}</span></li>
        `).join("")}
      </ol>
      <div class="dry-run-seal">Dry-Run abgeschlossen · Keine Kartendaten verändert</div>
      <button id="compare-card-button" class="compare-button" type="button">Mit eingelegter Karte abgleichen</button>
    `;
    comparisonTarget = { target_iccid: preview.iccid, target_imsi: preview.imsi, reader_index: 0 };
    dryRunReady = unknownCard; saveButton.disabled = !dryRunReady;
    comparisonPanel.hidden = true;
    document.querySelector("#compare-card-button").addEventListener("click", compareCard);
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    submitButton.disabled = false;
  }
});

readCardButton.addEventListener("click", async () => {
  readCardButton.disabled = true; cardStatus.hidden = false; cardStatus.textContent = "Karte wird ausschließlich gelesen …";
  unknownCard = false; dryRunReady = false; saveButton.disabled = true;
  try {
    const response = await fetch("/api/v1/sim/read", {method: "POST", cache: "no-store"});
    const identity = await response.json();
    if (!response.ok) throw new Error(identity.detail?.message || "Karte konnte nicht gelesen werden.");
    form.iccid.value = identity.iccid; form.imsi.value = identity.imsi;
    const lookup = await fetch(`/api/v1/profiles/by-iccid/${encodeURIComponent(identity.iccid)}`, {cache: "no-store"});
    const existing = await lookup.json();
    if (existing) {
      cardStatus.textContent = `Diese Karte ist bereits als Revision ${existing.revision} im Profiltresor vorhanden. Es wird keine Dublette angelegt.`;
      panel.innerHTML = `<p class="eyebrow">Vorhandene Karte</p><h2>${escapeHtml(identity.iccid)}</h2><p>Öffne den Profiltresor, um das bestehende Profil zu prüfen oder eine Änderung vorzubereiten.</p><a class="button-link" href="/profiles">Zum Profiltresor</a>`;
    } else {
      unknownCard = true;
      cardStatus.textContent = "Unbekannte Karte erkannt. Ergänze die geheimen Profildaten und führe vor dem Speichern den Dry Run aus.";
    }
  } catch (error) { cardStatus.textContent = error.message; form.iccid.value = ""; form.imsi.value = ""; }
  finally { readCardButton.disabled = false; }
});

form.addEventListener("input", (event) => {
  if (event.target.name !== "password") { dryRunReady = false; saveButton.disabled = true; }
});

saveButton.addEventListener("click", async () => {
  errorMessage.hidden = true;
  if (!unknownCard || !dryRunReady) { errorMessage.textContent = "Karte erneut prüfen und anschließend einen aktuellen Dry Run erstellen."; errorMessage.hidden = false; return; }
  if (!form.reportValidity()) return;
  saveButton.disabled = true;
  const values = new FormData(form);
  const payload = {...profileFields(values), reader_index: 0, verify_card: captureMode === "card", password: values.get("password")};
  try {
    const response = await fetch("/api/v1/profiles/single", {method: "POST", headers: {"Content-Type": "application/json", "Cache-Control": "no-store"}, body: JSON.stringify(payload), cache: "no-store"});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail?.message || result.detail || "Profil konnte nicht gespeichert werden.");
    unknownCard = false; dryRunReady = false; form.ki.value = ""; form.opc.value = ""; form.adm.value = ""; form.password.value = "";
    cardStatus.textContent = result.card_verified ? `Profil wurde kartengeprüft und verschlüsselt als Revision ${result.revision} gespeichert. Die SIM-Karte wurde nicht verändert.` : `Profil wurde verschlüsselt als Revision ${result.revision} gespeichert. Der Kartenabgleich ist noch ausstehend.`;
    panel.innerHTML = `<p class="eyebrow">Einzelerfassung abgeschlossen</p><h2>${escapeHtml(result.iccid)}</h2><p>Das Profil liegt jetzt im Profiltresor. Änderungen am Kartenstand werden dort als kontrollierter Entwurf vorbereitet.</p><a class="button-link" href="/profiles">Zum Profiltresor</a>`;
  } catch (error) { errorMessage.textContent = error.message; errorMessage.hidden = false; saveButton.disabled = false; }
});

async function compareCard() {
  const button = document.querySelector("#compare-card-button");
  button.disabled = true;
  button.textContent = "Karte wird gelesen …";
  try {
    const response = await fetch("/api/v1/provisioning/card-comparison", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(comparisonTarget),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail?.message || "Kartenabgleich fehlgeschlagen");
    const matchClass = (matches) => matches ? "comparison-match" : "comparison-difference";
    const matchLabel = (matches) => matches ? "Stimmt überein" : "Weicht ab";
    comparisonPanel.className = "preview-panel comparison-panel";
    comparisonPanel.innerHTML = `
      <p class="eyebrow">Kartenabgleich · Nur Lesen</p>
      <h2>${escapeHtml(result.card_type)}</h2>
      <dl class="comparison-list">
        <div><dt>ICCID der Karte</dt><dd>${escapeHtml(result.current_iccid)}</dd><strong class="${matchClass(result.iccid_matches)}">${matchLabel(result.iccid_matches)}</strong></div>
        <div><dt>IMSI der Karte</dt><dd>${escapeHtml(result.current_imsi)}</dd><strong class="${matchClass(result.imsi_matches)}">${matchLabel(result.imsi_matches)}</strong></div>
        <div><dt>ATR</dt><dd>${escapeHtml(result.atr)}</dd></div>
      </dl>
      <div class="dry-run-seal">Kartenabgleich abgeschlossen · Keine Daten verändert</div>
    `;
    comparisonPanel.hidden = false;
  } catch (error) {
    comparisonPanel.className = "preview-panel comparison-panel comparison-error";
    comparisonPanel.textContent = error.message;
    comparisonPanel.hidden = false;
  } finally {
    button.disabled = false;
    button.textContent = "Mit eingelegter Karte abgleichen";
  }
}
