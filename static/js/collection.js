const state = {
  items: [],
  categories: [],
  summary: {},
  filter: "ALL",
  addCategory: "",
};

const categoryColors = {
  "ETB/BUNDLE": "#2f6bff",
  "COFFRET": "#b12cff",
  "TINS": "#00d084",
  "POKEBOX": "#ff2fa8",
  "TRIPACK/DUOPACK": "#ff8a2a",
  "BOOSTER À L'UNITÉ/ARTSET": "#8ea0ff",
};

document.addEventListener("DOMContentLoaded", () => {
  bindNavigation();
  buildManualCollection();
  bindStaticEvents();
  loadCollection();
  if (location.pathname === "/marche") switchView("marche");
});

function bindNavigation() {
  document.querySelectorAll(".nav-tab").forEach(button => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });
}

function switchView(view) {
  document.querySelectorAll(".nav-tab").forEach(tab => tab.classList.toggle("active", tab.dataset.view === view));
  document.querySelector("#collectionView").classList.toggle("active-view", view === "collection");
  document.querySelector("#marcheView").classList.toggle("active-view", view === "marche");
  history.replaceState(null, "", view === "marche" ? "/marche" : "/");
  if (view === "marche") loadMarket();
}

function buildManualCollection() {
  document.querySelector("#collectionView").innerHTML = `
    <section class="manual-hero">
      <div>
        <h1>PokéCollect</h1>
        <p>Portefeuille Pokémon scellé manuel, propre, rapide, avec liens CardMarket et PnL visible.</p>
      </div>
      <div class="hero-orbit" aria-hidden="true"></div>
    </section>

    <div class="stats-grid neon-stats">
      <article class="stat-card"><span class="stat-value" id="statItems">0</span><span class="stat-label">Items total</span></article>
      <article class="stat-card"><span class="stat-value" id="statCost">0,00 €</span><span class="stat-label">Prix acheté total</span></article>
      <article class="stat-card"><span class="stat-value" id="statMarket">0,00 €</span><span class="stat-label">Prix marché total</span></article>
      <article class="stat-card"><span class="stat-value" id="statPnl">0,00 €</span><span class="stat-label" id="statPnlPct">PnL 0%</span></article>
    </div>

    <div class="manual-toolbar">
      <label class="select-wrap">
        <span>Filtrer</span>
        <select id="manualCategoryFilter"><option value="ALL">Toutes les catégories</option></select>
      </label>
      <button class="ghost-action" id="manualExportBtn">Export CSV</button>
    </div>

    <div id="manualTables" class="manual-tables"></div>

    <div class="modal-backdrop hidden" id="manualModal" role="dialog" aria-modal="true">
      <form class="manual-modal" id="manualForm">
        <button class="icon-close" type="button" id="manualCloseBtn" aria-label="Fermer">×</button>
        <h2 id="manualModalTitle">Ajouter un item</h2>
        <label>Nom de l'item<input name="nom" required placeholder="ETB Chaos Ascendant"></label>
        <div class="modal-grid-2">
          <label>Quantité<input name="quantite" type="number" min="1" value="1" required></label>
          <label>Prix acheté (€)<input name="prix_achete" type="number" min="0" step="0.01" value="0" required></label>
        </div>
        <div class="modal-grid-2">
          <label>Prix marché (€)<input name="prix_marche" type="number" min="0" step="0.01" value="0"></label>
          <label>Catégorie<select name="categorie" required></select></label>
        </div>
        <label>Lien CardMarket<input name="price_source_url" type="url" placeholder="https://www.cardmarket.com/fr/Pokemon/..."></label>
        <button class="primary-action form-submit" type="submit">Ajouter au tableau</button>
      </form>
    </div>
  `;
}

function bindStaticEvents() {
  document.querySelector("#manualCategoryFilter").addEventListener("change", event => {
    state.filter = event.target.value;
    renderTables();
  });
  document.querySelector("#manualExportBtn").addEventListener("click", () => {
    window.location.href = "/api/export/csv";
  });
  document.querySelector("#manualCloseBtn").addEventListener("click", closeManualModal);
  document.querySelector("#manualModal").addEventListener("click", event => {
    if (event.target.id === "manualModal") closeManualModal();
  });
  document.querySelector("#manualForm").addEventListener("submit", submitManualItem);
}

async function loadCollection() {
  const payload = await api.collection();
  state.items = payload.collection.items;
  state.categories = payload.categories;
  state.summary = payload.summary;
  renderOptions();
  renderStats();
  renderTables();
  document.querySelector("#lastSync").textContent = `Dernière sauvegarde : ${dateLabel(payload.collection.last_updated)}`;
}

function renderOptions() {
  const options = state.categories.map(category => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join("");
  document.querySelector("#manualCategoryFilter").innerHTML = `<option value="ALL">Toutes les catégories</option>${options}`;
  document.querySelector('#manualForm [name="categorie"]').innerHTML = options;
}

function renderStats() {
  document.querySelector("#statItems").textContent = state.summary.total_units || 0;
  document.querySelector("#statCost").textContent = euro(state.summary.total_cost);
  document.querySelector("#statMarket").textContent = euro(state.summary.total_market);
  const pnl = Number(state.summary.pnl || 0);
  const pnlEl = document.querySelector("#statPnl");
  pnlEl.textContent = euro(pnl);
  pnlEl.classList.toggle("positive", pnl >= 0);
  pnlEl.classList.toggle("negative", pnl < 0);
  document.querySelector("#statPnlPct").textContent = `PnL ${Number(state.summary.pnl_pct || 0).toFixed(1)}%`;
}

function renderTables() {
  const categories = state.filter === "ALL" ? state.categories : [state.filter];
  document.querySelector("#manualTables").innerHTML = categories.map(renderCategoryTable).join("");
  bindTableEvents();
}

function renderCategoryTable(category) {
  const items = state.items.filter(item => item.categorie === category);
  const color = categoryColors[category] || "#ffd700";
  const totalBuy = items.reduce((sum, item) => sum + Number(item.prix_achete || 0) * Number(item.quantite || 0), 0);
  const totalMarket = items.reduce((sum, item) => sum + Number(item.prix_marche || 0) * Number(item.quantite || 0), 0);
  const pnl = totalMarket - totalBuy;
  return `
    <section class="manual-category" style="--category-color:${color}">
      <header class="manual-category-head">
        <h2>${escapeHtml(category)}</h2>
        <div>${items.length} lignes · Achat ${euro(totalBuy)} · Marché ${euro(totalMarket)} · <strong class="${pnl >= 0 ? "positive" : "negative"}">${euro(pnl)}</strong></div>
      </header>
      <div class="manual-table-wrap">
        <table class="manual-table">
          <thead>
            <tr>
              <th>Nom</th>
              <th>Qté</th>
              <th>Prix acheté</th>
              <th>Prix marché</th>
              <th>Total marché</th>
              <th>PnL</th>
              <th>Lien</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${items.map(renderItemRow).join("") || `<tr><td colspan="8" class="empty-row">Aucun item dans cette catégorie.</td></tr>`}
            <tr class="manual-add-row">
              <td colspan="8"><button class="add-line-btn" data-add-category="${escapeHtml(category)}">+ Ajouter dans ${escapeHtml(category)}</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function renderItemRow(item) {
  const totalMarket = Number(item.prix_marche || 0) * Number(item.quantite || 0);
  const totalBuy = Number(item.prix_achete || 0) * Number(item.quantite || 0);
  const pnl = totalMarket - totalBuy;
  const link = item.price_source_url
    ? `<a class="neon-link" href="${escapeHtml(item.price_source_url)}" target="_blank" rel="noreferrer">CardMarket</a>`
    : `<span class="muted">Aucun lien</span>`;
  return `
    <tr data-id="${escapeHtml(item.id)}">
      <td><span class="editable-cell" data-field="nom" data-type="text">${escapeHtml(item.nom)}</span></td>
      <td><span class="editable-cell" data-field="quantite" data-type="number">${item.quantite || 0}</span></td>
      <td><span class="editable-cell" data-field="prix_achete" data-type="money">${euro(item.prix_achete)}</span></td>
      <td><span class="editable-cell" data-field="prix_marche" data-type="money">${euro(item.prix_marche)}</span></td>
      <td>${euro(totalMarket)}</td>
      <td class="${pnl >= 0 ? "positive" : "negative"}">${euro(pnl)}</td>
      <td>
        ${link}
        <button class="mini-link-btn" data-link-edit title="Modifier le lien">✎</button>
      </td>
      <td><button class="icon-btn" data-delete title="Supprimer">🗑️</button></td>
    </tr>
  `;
}

function bindTableEvents() {
  document.querySelectorAll("[data-add-category]").forEach(button => {
    button.addEventListener("click", () => openManualModal(button.dataset.addCategory));
  });
  document.querySelectorAll(".editable-cell").forEach(cell => {
    cell.addEventListener("click", () => startEdit(cell));
  });
  document.querySelectorAll("[data-link-edit]").forEach(button => {
    button.addEventListener("click", event => editLink(event.target.closest("tr").dataset.id));
  });
  document.querySelectorAll("[data-delete]").forEach(button => {
    button.addEventListener("click", async event => {
      const id = event.target.closest("tr").dataset.id;
      if (!confirm("Supprimer cet item ?")) return;
      await api.deleteItem(id);
      await loadCollection();
    });
  });
}

function openManualModal(category) {
  state.addCategory = category;
  const form = document.querySelector("#manualForm");
  form.reset();
  form.categorie.value = category;
  form.quantite.value = 1;
  form.prix_achete.value = 0;
  form.prix_marche.value = 0;
  document.querySelector("#manualModalTitle").textContent = `Ajouter · ${category}`;
  document.querySelector("#manualModal").classList.remove("hidden");
  form.nom.focus();
}

function closeManualModal() {
  document.querySelector("#manualModal").classList.add("hidden");
}

async function submitManualItem(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = Object.fromEntries(form.entries());
  payload.quantite = Number(payload.quantite || 1);
  payload.prix_achete = Number(payload.prix_achete || 0);
  payload.prix_marche = Number(payload.prix_marche || 0);
  payload.search_query = payload.nom;
  payload.price_source = payload.price_source_url ? "CardMarket manuel" : "";
  payload.price_status = "manual";
  payload.derniere_maj = new Date().toISOString().slice(0, 19);
  await api.addItem(payload);
  closeManualModal();
  await loadCollection();
}

function startEdit(cell) {
  const row = cell.closest("tr");
  const id = row.dataset.id;
  const item = state.items.find(entry => entry.id === id);
  const field = cell.dataset.field;
  const input = document.createElement("input");
  input.className = "inline-input";
  input.type = cell.dataset.type === "text" ? "text" : "number";
  if (input.type === "number") {
    input.step = field === "quantite" ? "1" : "0.01";
    input.min = "0";
  }
  input.value = item[field] ?? "";
  cell.replaceWith(input);
  input.focus();
  input.select();

  const save = async () => {
    const value = input.type === "number" ? Number(input.value || 0) : input.value.trim();
    await api.updateItem(id, { [field]: value, derniere_maj: new Date().toISOString().slice(0, 19) });
    await loadCollection();
  };
  input.addEventListener("blur", save, { once: true });
  input.addEventListener("keydown", event => {
    if (event.key === "Enter") input.blur();
    if (event.key === "Escape") loadCollection();
  });
}

async function editLink(id) {
  const item = state.items.find(entry => entry.id === id);
  const value = prompt("Lien CardMarket de l'item :", item.price_source_url || "");
  if (value === null) return;
  await api.updateItem(id, {
    price_source_url: value.trim(),
    price_source: value.trim() ? "CardMarket manuel" : "",
    derniere_maj: new Date().toISOString().slice(0, 19),
  });
  await loadCollection();
}
