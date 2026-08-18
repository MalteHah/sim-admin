const form = document.querySelector("#import-form");
const message = document.querySelector("#import-message");
const result = document.querySelector("#import-result");
const rows = document.querySelector("#import-rows");
const storeButton = document.querySelector("#store-import");
let validatedContent = null;
const importPaginator = window.createTablePaginator(document.querySelector("#import-pagination"), (items) => {
  rows.replaceChildren();
  for (const item of items) {
    const row = document.createElement("tr");
    for (const value of [item.row_number, item.iccid, item.imsi, item.valid ? "Gültig" : item.errors.join("; ")]) { const cell = document.createElement("td"); cell.textContent = value; row.append(cell); }
    rows.append(row);
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault(); message.hidden = true; result.hidden = true; storeButton.hidden = true; validatedContent = null;
  const file = document.querySelector("#csv-file").files[0];
  if (!file || file.size > 2000000) { message.textContent = "Die Datei fehlt oder ist größer als 2 MB."; message.hidden = false; return; }
  const response = await fetch("/api/v1/imports/csv/preview", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({content: await file.text()})});
  const preview = await response.json();
  if (!response.ok) { message.textContent = preview.detail?.message || "CSV-Prüfung fehlgeschlagen."; message.hidden = false; return; }
  message.className = preview.invalid_rows ? "form-error" : "form-success";
  message.textContent = `${preview.valid_rows} gültig, ${preview.invalid_rows} fehlerhaft. Keine Daten gespeichert.`; message.hidden = false;
  importPaginator.setItems(preview.rows);
  result.hidden = false;
  if (preview.invalid_rows === 0) { validatedContent = await file.text(); storeButton.hidden = false; }
});

storeButton.addEventListener("click", async () => {
  if (!validatedContent || !window.confirm("Alle gültigen Profile jetzt gerätegebunden verschlüsselt speichern?")) return;
  storeButton.disabled = true;
  const response = await fetch("/api/v1/profiles/import", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({content: validatedContent})});
  const payload = await response.json(); message.hidden = false;
  message.className = response.ok ? "form-success" : "form-error";
  message.textContent = response.ok ? `${payload.imported} Profile wurden verschlüsselt gespeichert.` : (payload.detail?.message || "Profile konnten nicht gespeichert werden.");
  if (response.ok) { validatedContent = null; storeButton.hidden = true; }
  storeButton.disabled = false;
});
