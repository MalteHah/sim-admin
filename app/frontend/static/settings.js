const form = document.querySelector("#password-form");
const message = document.querySelector("#password-message");
const submitButton = form.querySelector("button[type='submit']");
const suciForm = document.querySelector("#suci-key-form");
const suciMessage = document.querySelector("#suci-key-message");
const suciList = document.querySelector("#suci-key-list");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.hidden = true;
  if (form.newPassword.value !== form.confirmPassword.value) {
    message.textContent = "Die neuen Passwörter stimmen nicht überein.";
    message.hidden = false;
    return;
  }
  submitButton.disabled = true;
  try {
    const response = await fetch("/api/v1/settings/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: form.currentPassword.value,
        new_password: form.newPassword.value,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail?.message || "Änderung fehlgeschlagen");
    form.reset();
    message.className = "form-success";
    message.textContent = "Passwort wurde erfolgreich geändert.";
    message.hidden = false;
  } catch (error) {
    message.className = "form-error";
    message.textContent = error.message;
    message.hidden = false;
  } finally {
    submitButton.disabled = false;
  }
});

async function responseError(response, fallback) {
  try { const payload = await response.json(); return typeof payload.detail === "string" ? payload.detail : payload.detail?.message || fallback; }
  catch (_) { return fallback; }
}

function hexFingerprint(value) {
  return value.match(/.{1,4}/g)?.join(" ") || value;
}

async function loadSuciKeys() {
  const response = await fetch("/api/v1/settings/suci-keys", {cache: "no-store"});
  if (!response.ok) { suciList.textContent = "Schlüssel konnten nicht geladen werden."; return; }
  const keys = await response.json(); suciList.replaceChildren();
  if (!keys.length) { suciList.textContent = "Noch kein öffentlicher Heimnetzschlüssel importiert."; return; }
  for (const key of keys) {
    const card = document.createElement("article"); card.className = `suci-key-card${key.active ? "" : " is-inactive"}`;
    const title = document.createElement("h4"); title.textContent = key.name;
    const meta = document.createElement("p"); meta.textContent = `Profile ${key.scheme === 1 ? "A" : "B"} · Open5GS Key ID ${key.key_id} · ${key.active ? "Aktiv" : "Inaktiv"}${key.in_use ? " · In Verwendung" : ""}`;
    const fingerprint = document.createElement("code"); fingerprint.textContent = `SHA-256 ${hexFingerprint(key.fingerprint)}`;
    const actions = document.createElement("div"); actions.className = "table-actions";
    const toggle = document.createElement("button"); toggle.type = "button"; toggle.textContent = key.active ? "Deaktivieren" : "Aktivieren";
    toggle.addEventListener("click", () => changeSuciKey(key.id, !key.active)); actions.append(toggle);
    const remove = document.createElement("button"); remove.type = "button"; remove.className = "danger-button"; remove.textContent = "Löschen"; remove.disabled = key.in_use;
    remove.title = key.in_use ? "Verwendete Schlüssel können nicht gelöscht werden" : "Unbenutzten Schlüssel löschen";
    remove.addEventListener("click", () => deleteSuciKey(key.id, key.name)); actions.append(remove);
    card.append(title, meta, fingerprint, actions); suciList.append(card);
  }
}

async function operationPassword() {
  const password = document.querySelector("#suci-key-password").value;
  if (!password) { suciMessage.textContent = "Bitte das aktuelle Admin-Passwort eingeben."; suciMessage.hidden = false; return null; }
  return password;
}

async function changeSuciKey(id, active) {
  const password = await operationPassword(); if (!password) return;
  const response = await fetch(`/api/v1/settings/suci-keys/${id}`, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify({password, active})});
  if (!response.ok) { suciMessage.textContent = await responseError(response, "Status konnte nicht geändert werden."); suciMessage.hidden = false; return; }
  suciMessage.className = "form-success"; suciMessage.textContent = active ? "Schlüssel wurde aktiviert." : "Schlüssel wurde deaktiviert."; suciMessage.hidden = false; await loadSuciKeys();
}

async function deleteSuciKey(id, name) {
  if (!window.confirm(`Den unbenutzten Schlüssel „${name}“ wirklich löschen?`)) return;
  const password = await operationPassword(); if (!password) return;
  const response = await fetch(`/api/v1/settings/suci-keys/${id}`, {method: "DELETE", headers: {"Content-Type": "application/json"}, body: JSON.stringify({password})});
  if (!response.ok) { suciMessage.textContent = await responseError(response, "Schlüssel konnte nicht gelöscht werden."); suciMessage.hidden = false; return; }
  suciMessage.className = "form-success"; suciMessage.textContent = "Schlüssel wurde gelöscht."; suciMessage.hidden = false; await loadSuciKeys();
}

suciForm.addEventListener("submit", async (event) => {
  event.preventDefault(); suciMessage.hidden = true;
  const file = document.querySelector("#suci-key-file").files[0]; if (!file) return;
  const bytes = new Uint8Array(await file.arrayBuffer());
  const decoded = new TextDecoder().decode(bytes);
  const isText = decoded.includes("-----BEGIN") || /^[0-9A-Fa-f:\s]+$/.test(decoded);
  const keyData = isText ? decoded : `base64:${btoa(Array.from(bytes, byte => String.fromCharCode(byte)).join(""))}`;
  const submit = suciForm.querySelector('button[type="submit"]'); submit.disabled = true;
  const response = await fetch("/api/v1/settings/suci-keys", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({
    password: document.querySelector("#suci-key-password").value, name: document.querySelector("#suci-key-name").value,
    scheme: Number(document.querySelector("#suci-key-scheme").value), key_id: Number(document.querySelector("#suci-key-id").value), key_data: keyData,
  })});
  submit.disabled = false;
  if (!response.ok) { suciMessage.className = "form-error"; suciMessage.textContent = await responseError(response, "Import fehlgeschlagen."); suciMessage.hidden = false; return; }
  suciForm.reset(); document.querySelector("#suci-key-id").value = "1"; suciMessage.className = "form-success"; suciMessage.textContent = "Öffentlicher Schlüssel wurde geprüft und importiert."; suciMessage.hidden = false; await loadSuciKeys();
});

document.querySelector("#suci-key-refresh").addEventListener("click", loadSuciKeys);
loadSuciKeys();
