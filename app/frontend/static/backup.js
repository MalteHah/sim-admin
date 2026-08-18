const form = document.querySelector("#backup-form");
const target = document.querySelector("#backup-target");
const submit = document.querySelector("#backup-submit");
const message = document.querySelector("#backup-message");
const restoreForm = document.querySelector("#restore-form");
const restoreFile = document.querySelector("#restore-file");
const restoreMessage = document.querySelector("#restore-message");
const restoreButton = document.querySelector("#restore-submit");
let inspected = null;

function formatBytes(bytes) {
  return new Intl.NumberFormat("de-DE", { style: "unit", unit: "gigabyte", maximumFractionDigits: 1 }).format(bytes / 1e9);
}

async function loadTargets() {
  const response = await fetch("/api/v1/backups/targets");
  const targets = response.ok ? await response.json() : [];
  target.replaceChildren();
  if (!targets.length) {
    const option = document.createElement("option");
    option.textContent = "Kein eingebundener USB-Datenträger gefunden";
    target.append(option);
    return;
  }
  for (const item of targets) {
    const option = document.createElement("option");
    option.value = item.path;
    option.textContent = `${item.name} – ${formatBytes(item.free_bytes)} frei`;
    target.append(option);
  }
  target.disabled = false;
  submit.disabled = false;
  await loadBackups();
}

async function loadBackups() {
  const response = await fetch("/api/v1/backups");
  const backups = response.ok ? await response.json() : [];
  restoreFile.replaceChildren();
  for (const item of backups) {
    const option = document.createElement("option");
    option.value = JSON.stringify(item); option.textContent = item.filename; restoreFile.append(option);
  }
  restoreFile.disabled = !backups.length;
  document.querySelector("#inspect-submit").disabled = !backups.length;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.hidden = true;
  if (form.querySelector("#backup-password").value !== form.querySelector("#backup-confirm").value) {
    message.textContent = "Die Passwörter stimmen nicht überein.";
    message.hidden = false;
    return;
  }
  submit.disabled = true;
  const response = await fetch("/api/v1/backups", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_path: target.value, password: form.querySelector("#backup-password").value }),
  });
  const result = await response.json();
  message.className = response.ok ? "form-success" : "form-error";
  message.textContent = response.ok
    ? `Backup ${result.filename} wurde verschlüsselt und geprüft.`
    : (result.detail?.message || "Backup konnte nicht erstellt werden.");
  message.hidden = false;
  form.querySelector("#backup-password").value = "";
  form.querySelector("#backup-confirm").value = "";
  submit.disabled = false;
  await loadBackups();
});

restoreForm.addEventListener("submit", async (event) => {
  event.preventDefault(); inspected = JSON.parse(restoreFile.value);
  const request = {target_path: inspected.target_path, filename: inspected.filename, password: document.querySelector("#restore-password").value};
  const response = await fetch("/api/v1/backups/inspect", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(request)});
  const result = await response.json();
  restoreMessage.hidden = false; restoreMessage.className = response.ok ? "form-success" : "form-error";
  restoreMessage.textContent = response.ok ? `Backup vom ${new Date(result.created_at).toLocaleString("de-DE")} ist vollständig und kompatibel.` : (result.detail?.message || "Prüfung fehlgeschlagen.");
  restoreButton.hidden = !response.ok;
});

restoreButton.addEventListener("click", async () => {
  if (!inspected || !window.confirm("Das aktuelle Aktivitätsprotokoll wird ersetzt. Wirklich wiederherstellen?")) return;
  restoreButton.disabled = true;
  const request = {target_path: inspected.target_path, filename: inspected.filename, password: document.querySelector("#restore-password").value, confirmation: "WIEDERHERSTELLEN"};
  const response = await fetch("/api/v1/backups/restore", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(request)});
  const result = await response.json(); restoreMessage.hidden = false;
  restoreMessage.className = response.ok ? "form-success" : "form-error";
  restoreMessage.textContent = response.ok ? "Backup wurde erfolgreich wiederhergestellt." : (result.detail?.message || "Wiederherstellung fehlgeschlagen.");
  restoreButton.disabled = false;
});

loadTargets();
