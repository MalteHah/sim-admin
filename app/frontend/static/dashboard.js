const readerList = document.querySelector("#reader-list");
const serviceStatus = document.querySelector("#service-status");
const refreshButton = document.querySelector("#refresh-button");
const logoutButton = document.querySelector("#logout-button");
const readSimButton = document.querySelector("#read-sim-button");
const simResult = document.querySelector("#sim-result");

const stateLabels = {
  ready: "Bereit – keine Karte",
  card_present: "Karte erkannt",
  error: "Reader-Fehler",
  disconnected: "Nicht verbunden",
};

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}

function renderReaders(readers) {
  readSimButton.disabled = !readers.some((reader) => reader.status === "card_present");
  if (readers.length === 0) {
    readerList.innerHTML = '<div class="reader-card empty">Kein Kartenleser gefunden.</div>';
    return;
  }

  readerList.innerHTML = readers.map((reader) => `
    <article class="reader-card">
      <div class="reader-icon" aria-hidden="true"></div>
      <div>
        <p class="eyebrow">${escapeHtml(reader.reader_type || "Reader")}</p>
        <h3>${escapeHtml(reader.name)}</h3>
        <p class="reader-meta">ATR: ${escapeHtml(reader.atr || "Keine Karte eingelegt")}</p>
      </div>
      <span class="reader-state state-${escapeHtml(reader.status)}">
        ${escapeHtml(stateLabels[reader.status] || reader.status)}
      </span>
    </article>
  `).join("");
}

async function readSim() {
  readSimButton.disabled = true;
  readSimButton.textContent = "SIM wird gelesen …";
  simResult.hidden = true;
  try {
    const response = await fetch("/api/v1/sim/read", {
      method: "POST",
      headers: { Accept: "application/json" },
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail?.message || "SIM konnte nicht gelesen werden");
    simResult.className = "sim-result";
    simResult.innerHTML = `
      <div><span>Kartentyp</span><strong>${escapeHtml(payload.card_type)}</strong></div>
      <div><span>ICCID</span><strong>${escapeHtml(payload.iccid)}</strong></div>
      <div><span>IMSI</span><strong>${escapeHtml(payload.imsi)}</strong></div>
      <div><span>ATR</span><strong>${escapeHtml(payload.atr)}</strong></div>
    `;
    simResult.hidden = false;
  } catch (error) {
    simResult.className = "sim-result sim-error";
    simResult.textContent = error.message;
    simResult.hidden = false;
  } finally {
    readSimButton.textContent = "SIM lesen";
    await refreshReaders();
  }
}

async function refreshReaders() {
  refreshButton.disabled = true;
  try {
    const response = await fetch("/api/v1/readers", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    renderReaders(await response.json());
    serviceStatus.textContent = "System online";
    serviceStatus.className = "status";
  } catch (error) {
    readerList.innerHTML = '<div class="reader-card empty">Reader-Dienst derzeit nicht erreichbar.</div>';
    serviceStatus.textContent = "Verbindung gestört";
    serviceStatus.className = "status status-error";
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener("click", refreshReaders);
readSimButton.addEventListener("click", readSim);
logoutButton.addEventListener("click", async () => {
  await fetch("/logout", { method: "POST" });
  window.location.assign("/login");
});
refreshReaders();
setInterval(refreshReaders, 5000);
