const state = {
  items: [],
  categories: [],
  summary: {},
  collapsed: new Set(),
  filter: "ALL",
};

const categoryColors = {
  "ETB/BUNDLE": "#1a3a8f",
  "COFFRET": "#6b21a8",
  "TINS": "#14532d",
  "POKEBOX": "#be185d",
  "TRIPACK/DUOPACK": "#c2410c",
  "BOOSTER À L'UNITÉ/ARTSET": "#1f2937",
};

const collectionEls = {};

document.addEventListener("DOMContentLoaded", () => {
  bindElements();
  bindNavigation();
  bindModal();
  loadCollection();
  if (location.pathname === "/marche") switchView("marche");
});

function bindElements() {
  Object.assign(collectionEls, {
    table: document.querySelector("#collectionTable"),
    filter: document.querySelector("#categoryFilter"),
    lastSync: document.querySelector("#lastSync"),
    progressPanel: document.querySelector("#progressPanel"),
    progressText: document.querySelector("#progressText"),
    progressBar: document.querySelector("#progressBar"),
    modal: document.querySelector("#itemModal"),
    form: document.querySelector("#itemForm"),
    searchInput: document.querySelector("#productSearch"),
    searchResults: document.querySelector("#searchResults"),
    preview: document.querySelector("#formPreview"),
    lightbox: document.querySelector("#imageLightbox"),
    lightboxImage: document.querySelector("#lightboxImage"),
  });

  document.querySelector("#updateAllBtn").addEventListener("click", updateAllPrices);
  document.querySelector("#addItemBtn").addEventListener("click", openModal);
  document.querySelector("#closeModalBtn").addEventListener("click", closeModal);
  document.querySelector("#closeLightboxBtn").addEventListener("click", closeLightbox);
  document.querySelector("#searchProductBtn").addEventListener("click", searchProducts);
  document.querySelector("#refreshNewsBtn").addEventListener("click", loadMarket);
  collectionEls.filter.addEventListener("change", event => {
    state.filter = event.target.value;
    renderCollection();
  });
}

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

async function loadCollection() {
  const payload = await api.collection();
  state.items = payload.collection.items;
  state.categories = payload.categories;
  state.summary = payload.summary;
  renderCategoryOptions();
  renderStats();
  renderCollection();
  collectionEls.lastSync.textContent = `Dernière MAJ : ${dateLabel(payload.collection.last_updated)}`;
}

function renderCategoryOptions() {
  const formSelect = collectionEls.form.querySelector('[name="categorie"]');
  const options = state.categories.map(category => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join("");
  collectionEls.filter.innerHTML = `<option value="ALL">Toutes les catégories</option>${options}`;
  formSelect.innerHTML = options;
}

function renderStats() {
  document.querySelector("#statItems").textContent = state.summary.total_units || 0;
  document.querySelector("#statCost").textContent = euro(state.summary.total_cost);
  document.querySelector("#statMarket").textContent = euro(state.summary.total_market);
  const pnlEl = document.querySelector("#statPnl");
  const pnlPctEl = document.querySelector("#statPnlPct");
  pnlEl.textContent = euro(state.summary.pnl);
  pnlPctEl.textContent = `PnL ${Number(state.summary.pnl_pct || 0).toFixed(1)}%`;
  pnlEl.classList.toggle("positive", state.summary.pnl >= 0);
  pnlEl.classList.toggle("negative", state.summary.pnl < 0);
}

function renderCollection() {
  const categories = state.filter === "ALL" ? state.categories : [state.filter];
  collectionEls.table.innerHTML = categories.map(category => renderCategory(category)).join("");
  bindTableActions();
}

function renderCategory(category) {
  const items = state.items.filter(item => item.categorie === category);
  const totalCost = items.reduce((sum, item) => sum + Number(item.prix_achete || 0) * Number(item.quantite || 0), 0);
  const totalMarket = items.reduce((sum, item) => sum + Number(item.val_marche_totale || 0), 0);
  const collapsed = state.collapsed.has(category);
  const color = categoryColors[category] || "#1f2937";

  return `
    <section class="category-section" data-category="${escapeHtml(category)}">
      <button class="category-header" style="background:${color}" data-collapse="${escapeHtml(category)}">
        <span>${collapsed ? "▶" : "▼"} ${escapeHtml(category)}</span>
        <span>${items.length} lignes · Achat ${euro(totalCost)} · Marché ${euro(totalMarket)}</span>
      </button>
      <div class="table-wrap ${collapsed ? "hidden" : ""}">
        <table>
          <thead>
            <tr>
              <th>Image</th><th>Nom</th><th>Qté</th><th>Acheté</th><th>Marché</th>
              <th>Val. marché</th><th>%</th><th>Dernière MAJ</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${items.map(renderRow).join("")}
            <tr class="category-total" style="background:${color}22">
              <td></td><td>Total ${escapeHtml(category)}</td><td>${items.reduce((sum, item) => sum + Number(item.quantite || 0), 0)}</td>
              <td>${euro(totalCost)}</td><td></td><td>${euro(totalMarket)}</td><td></td><td></td><td></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  `;
}

function renderRow(item) {
  const variation = item.variation_pct;
  const up = Number(variation || 0) >= 0;
  const hot = variation !== null && Math.abs(Number(variation)) >= 20;
  const status = item.price_status === "failed" ? `<div class="status-warn">⚠️ Prix estimé le ${dateLabel(item.derniere_maj)}</div>` : "";
  return `
    <tr class="item-row" data-id="${escapeHtml(item.id)}">
      <td><img class="product-img" src="${escapeHtml(item.image_url || "/static/images/pokeball.svg")}" alt="${escapeHtml(item.nom)}" data-zoom></td>
      <td>
        <strong>${escapeHtml(item.nom)}</strong>
        <small title="Cliquer pour modifier la recherche eBay" class="editable search-edit" data-field="search_query" data-type="text">${escapeHtml(item.search_query || "")}</small>
        ${status}
      </td>
      <td><span class="editable" data-field="quantite" data-type="number">${item.quantite}</span></td>
      <td><span class="editable" data-field="prix_achete" data-type="money">${euro(item.prix_achete)}</span></td>
      <td>${item.prix_marche === null || item.prix_marche === undefined ? "—" : euro(item.prix_marche)} <button class="icon-btn" title="Mettre à jour ce prix" data-refresh>🔄</button></td>
      <td>${euro(item.val_marche_totale)}</td>
      <td>${variation === null || variation === undefined ? "—" : `<span class="variation-badge ${up ? "up" : "down"} ${hot ? "hot" : ""}">${up ? "▲" : "▼"} ${Math.abs(Number(variation)).toFixed(1)}%</span>`}</td>
      <td title="${escapeHtml(item.derniere_maj || "")}">${dateLabel(item.derniere_maj)}</td>
      <td><button class="icon-btn" title="Supprimer" data-delete>🗑️</button></td>
    </tr>
  `;
}

function bindTableActions() {
  document.querySelectorAll("[data-collapse]").forEach(button => {
    button.addEventListener("click", () => {
      const category = button.dataset.collapse;
      state.collapsed.has(category) ? state.collapsed.delete(category) : state.collapsed.add(category);
      renderCollection();
    });
  });

  document.querySelectorAll("[data-refresh]").forEach(button => {
    button.addEventListener("click", async event => {
      const id = event.target.closest("tr").dataset.id;
      button.disabled = true;
      button.textContent = "⏳";
      await api.updatePrice(id);
      await loadCollection();
    });
  });

  document.querySelectorAll("[data-delete]").forEach(button => {
    button.addEventListener("click", async event => {
      const row = event.target.closest("tr");
      const item = state.items.find(entry => entry.id === row.dataset.id);
      if (!confirm(`Supprimer "${item.nom}" ?`)) return;
      await api.deleteItem(row.dataset.id);
      await loadCollection();
    });
  });

  document.querySelectorAll(".editable").forEach(element => {
    element.addEventListener("click", () => startInlineEdit(element));
  });

  document.querySelectorAll("[data-zoom]").forEach(image => {
    image.addEventListener("click", () => {
      const src = image.src || "";
      if (!src || src.includes("pokeball") || !image.complete || image.naturalWidth === 0) return;
      openLightbox(src);
    });
  });
}

function startInlineEdit(element) {
  const row = element.closest("tr");
  const item = state.items.find(entry => entry.id === row.dataset.id);
  const field = element.dataset.field;
  const input = document.createElement("input");
  input.type = element.dataset.type === "text" ? "text" : "number";
  if (input.type === "number") {
    input.step = field === "quantite" ? "1" : "0.01";
    input.min = "0";
  }
  input.value = item[field] || 0;
  element.replaceWith(input);
  input.focus();
  input.select();

  const save = async () => {
    const value = input.type === "number" ? Number(input.value) : input.value.trim();
    await api.updateItem(item.id, { [field]: value });
    await loadCollection();
  };
  input.addEventListener("blur", save, { once: true });
  input.addEventListener("keydown", event => {
    if (event.key === "Enter") input.blur();
    if (event.key === "Escape") loadCollection();
  });
}

async function updateAllPrices() {
  collectionEls.progressPanel.classList.remove("hidden");
  collectionEls.progressText.textContent = "Démarrage de la mise à jour...";
  collectionEls.progressBar.style.width = "0%";
  await api.updateAllPrices();
  const events = new EventSource("/api/price/stream");
  events.onmessage = async event => {
    const data = JSON.parse(event.data);
    if (data.type === "progress") {
      const pct = Math.round((data.current / data.total) * 100);
      collectionEls.progressText.textContent = `Mise à jour : ${data.item} (${data.current}/${data.total})`;
      collectionEls.progressBar.style.width = `${pct}%`;
    }
    if (data.type === "item_done") {
      const index = state.items.findIndex(item => item.id === data.item.id);
      if (index >= 0) state.items[index] = data.item;
      renderCollection();
    }
    if (data.type === "complete") {
      events.close();
      collectionEls.progressText.textContent = data.message;
      await loadCollection();
      setTimeout(() => collectionEls.progressPanel.classList.add("hidden"), 2500);
    }
  };
}

function bindModal() {
  collectionEls.form.addEventListener("submit", async event => {
    event.preventDefault();
    const form = new FormData(collectionEls.form);
    const payload = Object.fromEntries(form.entries());
    payload.quantite = Number(payload.quantite);
    payload.prix_achete = Number(payload.prix_achete);
    const added = await api.addItem(payload);
    closeModal();
    await api.updatePrice(added.item.id).catch(() => null);
    await loadCollection();
  });
}

function openModal() {
  collectionEls.modal.classList.remove("hidden");
  collectionEls.form.reset();
  collectionEls.form.quantite.value = 1;
  collectionEls.form.prix_achete.value = 0;
  collectionEls.form.image_url.value = "/static/images/pokeball.svg";
  collectionEls.preview.src = "/static/images/pokeball.svg";
  collectionEls.searchResults.innerHTML = "";
  collectionEls.searchInput.focus();
}

function closeModal() {
  collectionEls.modal.classList.add("hidden");
}

async function searchProducts() {
  const query = collectionEls.searchInput.value.trim();
  if (!query) return;
  collectionEls.searchResults.innerHTML = `<div class="result-card">Recherche...</div>`;
  const payload = await api.searchProduct(query);
  collectionEls.searchResults.innerHTML = payload.results.map(result => `
    <button type="button" class="result-card" data-result='${escapeHtml(JSON.stringify(result))}'>
      <img src="${escapeHtml(result.image_url || "/static/images/pokeball.svg")}" alt="">
      <strong>${escapeHtml(result.nom)}</strong>
      <small>${result.prix_estime ? euro(result.prix_estime) : "Prix à estimer"}</small>
    </button>
  `).join("");
  document.querySelectorAll("[data-result]").forEach(card => {
    card.addEventListener("click", () => selectResult(JSON.parse(card.dataset.result)));
  });
}

function selectResult(result) {
  collectionEls.form.nom.value = result.nom;
  collectionEls.form.search_query.value = result.search_query || result.nom;
  collectionEls.form.image_url.value = result.image_url || "/static/images/pokeball.svg";
  collectionEls.preview.src = result.image_url || "/static/images/pokeball.svg";
}

function openLightbox(src) {
  collectionEls.lightboxImage.src = src;
  collectionEls.lightbox.classList.remove("hidden");
  history.pushState({ lightbox: true }, "");
}

function closeLightbox() {
  collectionEls.lightbox.classList.add("hidden");
}

window.addEventListener("popstate", (event) => {
  if (!collectionEls.lightbox.classList.contains("hidden")) {
    closeLightbox();
  }
});
