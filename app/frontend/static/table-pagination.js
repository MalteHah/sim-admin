window.createTablePaginator = function createTablePaginator(container, renderPage, pageSize = 25) {
  let items = [];
  let page = 1;
  const previous = document.createElement("button");
  const label = document.createElement("span");
  const next = document.createElement("button");
  previous.type = next.type = "button";
  previous.textContent = "Zurück";
  next.textContent = "Weiter";
  container.replaceChildren(previous, label, next);

  function render() {
    const pages = Math.max(1, Math.ceil(items.length / pageSize));
    page = Math.min(Math.max(page, 1), pages);
    const start = (page - 1) * pageSize;
    renderPage(items.slice(start, start + pageSize));
    label.textContent = `Seite ${page} von ${pages} · ${items.length} Einträge`;
    previous.disabled = page === 1;
    next.disabled = page === pages;
    container.hidden = items.length <= pageSize;
  }

  previous.addEventListener("click", () => { page -= 1; render(); });
  next.addEventListener("click", () => { page += 1; render(); });
  return { setItems(newItems) { items = newItems; page = 1; render(); } };
};
