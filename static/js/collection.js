const state = {
  items: [],
  summary: {},
  searchResults: [],
  selectedProduct: null,
  category: "",
};

const filters = ["", "ETB", "Booster", "Display", "Bundle", "Coffret", "Tin", "Blister", "Produit"];

document.addEventListener("DOMContentLoaded", () => {
  bindNavigation();
  buildV2Shell();
  bindV2Events();
  loadPortfolio();
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

function buildV2Shell() {
  document.querySelector("#collectionView").innerHTML = `
    <section class="v2-dashboard">
      <div class="stats-grid">
        <article class="stat-card"><span class="stat-value" id="statItems">0</span><span class="stat-label">Items portefeuille</span></article>
        <article class="stat-card"><span class="stat-value" id="statCost">0,00 €</span><span class="stat-label">Coût achat</span></article>
        <article class="stat-card"><span class="stat-value" id="statMarket">0,00 €</span><span class="stat-label">Valeur marché</span></article>
        <article class="stat-card"><span class="stat-value" id="statPnl">0,00 €</span><span class="stat-label" id="statPnlPct">PnL 0%</span></article>
      </div>

      <div class="v2-search-panel">
        <div class="v2-search-row">
          <input id="v2SearchInput" type="search" placeholder="Rechercher sur CardMarket : Perfect Order, Black Bolt, ETB...">
          <button class="primary-action" id="v2SearchBtn">Rechercher</button>
          <button class="ghost-action" id="v2RefreshAllBtn">Mettre à jour le portefeuille</button>
        </div>
        <div class="filter-pills" id="v2Filters"></div>
      </div>

      <div class="v2-main-grid">
        <section>
          <div class="section-heading"><h1>Résultats CardMarket</h1><span id="resultCount" class="muted"></span></div>
          <div id="v2Results" class="product-grid"></div>
        </section>
        <aside id="productDetail" class="product-detail empty-detail">
          <h2>Sélectionne un produit</h2>
          <p>Choisis le bon item CardMarket, vérifie le prix et ajoute-le à ton portefeuille.</p>
        </aside>
      </div>

      <section class="portfolio-section">
        <div class="section-heading">
          <h1>Mon portefeuille</h1>
          <a class="ghost-action export-link" href="/api/export/csv">Export CSV</a>
        </div>
        <div id="portfolioGrid" class="portfolio-grid"></div>
      </section>
    </section>
  `;

  document.querySelector("#v2Filters").innerHTML = filters.map(filter => `
    <button class="filter-pill ${filter === "" ? "active" : ""}" data-filter="${escapeHtml(filter)}">${filter || "Tout"}</button>
  `).join("");
}

function bindV2Events() {
  document.querySelector("#v2SearchBtn").addEventListener("click", runSearch);
  document.querySelector("#v2SearchInput").addEventListener("keydown", event => {
    if (event.key === "Enter") runSearch();
  });
  document.querySelector("#v2RefreshAllBtn").addEventListener("click", refreshPortfolio);
  document.querySelectorAll("[data-filter]").forEach(button => {
    button.addEventListener("click", () => {
      state.category = button.dataset.filter;
      document.querySelectorAll("[data-filter]").forEach(pill => pill.classList.toggle("active", pill === button));
      if (document.querySelector("#v2SearchInput").value.trim()) runSearch();
    });
  });
}

async function loadPortfolio() {
  const payload = await api.collection();
  state.items = payload.collection.items;
  state.summary = payload.summary;
  renderStats();
  renderPortfolio();
  document.querySelector("#lastSync").textContent = `Dernière MAJ : ${dateLabel(payload.collection.last_updated)}`;
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

async function runSearch() {
  const query = document.querySelector("#v2SearchInput").value.trim();
  if (!query) return;
  const resultsEl = document.querySelector("#v2Results");
  resultsEl.innerHTML = `<div class="loading-card">Recherche CardMarket...</div>`;
  document.querySelector("#resultCount").textContent = "";
  const payload = await api.searchProduct(query, state.category);
  state.searchResults = payload.results || [];
  document.querySelector("#resultCount").textContent = `${state.searchResults.length} résultat(s)`;
  renderResults();
}

function renderResults() {
  const resultsEl = document.querySelector("#v2Results");
  if (!state.searchResults.length) {
    resultsEl.innerHTML = `<div class="loading-card">Aucun résultat. Essaie le nom anglais du set ou une recherche plus courte.</div>`;
    return;
  }
  resultsEl.innerHTML = state.searchResults.map((product, index) => `
    <button class="product-card" data-product-index="${index}">
      <img src="${escapeHtml(product.image_url || "/static/images/pokeball.svg")}" alt="">
      <span class="product-category">${escapeHtml(product.categorie || "Produit")}</span>
      <strong>${escapeHtml(product.nom)}</strong>
      <span>${product.prix_estime ? `À partir de ${euro(product.prix_estime)}` : "Prix indisponible"}</span>
    </button>
  `).join("");
  document.querySelectorAll("[data-product-index]").forEach(card => {
    card.addEventListener("click", () => selectProduct(Number(card.dataset.productIndex)));
  });
}

function selectProduct(index) {
  state.selectedProduct = state.searchResults[index];
  renderProductDetail();
}

function renderProductDetail() {
  const product = state.selectedProduct;
  const detail = document.querySelector("#productDetail");
  if (!product) return;
  detail.classList.remove("empty-detail");
  detail.innerHTML = `
    <div class="detail-media">
      <img src="${escapeHtml(product.image_url || "/static/images/pokeball.svg")}" alt="${escapeHtml(product.nom)}">
    </div>
    <div class="detail-body">
      <span class="product-category">${escapeHtml(product.categorie || "Produit")}</span>
      <h2>${escapeHtml(product.nom)}</h2>
      <div class="detail-price">${product.prix_estime ? euro(product.prix_estime) : "Prix indisponible"}</div>
      <canvas id="priceChart" width="520" height="220"></canvas>
      <div class="detail-meta">
        <span>Source : ${escapeHtml(product.price_source || "CardMarket")}</span>
        ${product.price_source_url ? `<a href="${escapeHtml(product.price_source_url)}" target="_blank" rel="noreferrer">Ouvrir CardMarket</a>` : ""}
      </div>
      <div class="add-form">
        <label>Quantité<input id="addQty" type="number" min="1" value="1"></label>
        <label>Prix acheté (€)<input id="addBuyPrice" type="number" min="0" step="0.01" value="${product.prix_estime || 0}"></label>
        <button class="primary-action" id="addToPortfolioBtn">Ajouter au portefeuille</button>
      </div>
    </div>
  `;
  drawChart(document.querySelector("#priceChart"), product.price_history || [], product.prix_estime);
  document.querySelector("#addToPortfolioBtn").addEventListener("click", addSelectedProduct);
}

function drawChart(canvas, history, currentPrice) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#111127";
  ctx.fillRect(0, 0, width, height);
  const points = history.length ? history : [{ price: currentPrice || 0 }];
  const values = points.map(point => Number(point.price || 0)).filter(Boolean);
  if (!values.length) {
    ctx.fillStyle = "#a0aec0";
    ctx.fillText("Historique indisponible", 24, 40);
    return;
  }
  const min = Math.min(...values) * 0.96;
  const max = Math.max(...values) * 1.04;
  ctx.strokeStyle = "rgba(255,255,255,.12)";
  ctx.lineWidth = 1;
  for (let i = 0; i < 5; i++) {
    const y = 24 + i * ((height - 48) / 4);
    ctx.beginPath();
    ctx.moveTo(36, y);
    ctx.lineTo(width - 20, y);
    ctx.stroke();
  }
  ctx.strokeStyle = "#ffd700";
  ctx.lineWidth = 3;
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = 36 + index * ((width - 68) / Math.max(1, values.length - 1));
    const y = height - 28 - ((value - min) / Math.max(1, max - min)) * (height - 58);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.fillStyle = "#ffffff";
  ctx.font = "14px DM Sans";
  ctx.fillText(`${euro(values[values.length - 1])}`, 40, 28);
}

async function addSelectedProduct() {
  const product = state.selectedProduct;
  if (!product) return;
  const payload = {
    id: `cm_${product.id || slugLike(product.nom)}`,
    nom: product.nom,
    categorie: mapCategory(product.categorie),
    product_category: product.categorie || "Produit",
    product_id: product.id || "",
    quantite: Number(document.querySelector("#addQty").value || 1),
    prix_achete: Number(document.querySelector("#addBuyPrice").value || 0),
    prix_marche: product.prix_estime || null,
    image_url: product.image_url || "/static/images/pokeball.svg",
    search_query: product.nom,
    price_source: product.price_source || "CardMarket API TCG",
    price_source_url: product.price_source_url || "",
    price_history: product.price_history || [],
    price_status: product.prix_estime ? "ok" : "pending",
    derniere_maj: new Date().toISOString().slice(0, 19),
  };
  await api.addItem(payload);
  await loadPortfolio();
}

function mapCategory(category) {
  if (category === "ETB") return "ETB/BUNDLE";
  if (category === "Bundle") return "ETB/BUNDLE";
  if (category === "Tin") return "TINS";
  if (category === "Blister") return "TRIPACK/DUOPACK";
  if (category === "Booster" || category === "Display") return "BOOSTER À L'UNITÉ/ARTSET";
  return "COFFRET";
}

function renderPortfolio() {
  const grid = document.querySelector("#portfolioGrid");
  if (!state.items.length) {
    grid.innerHTML = `<div class="loading-card">Ton portefeuille est vide. Recherche un produit CardMarket et ajoute-le.</div>`;
    return;
  }
  grid.innerHTML = state.items.map(item => `
    <article class="portfolio-card">
      <img src="${escapeHtml(item.image_url || "/static/images/pokeball.svg")}" alt="${escapeHtml(item.nom)}">
      <div>
        <span class="product-category">${escapeHtml(item.product_category || item.categorie || "Produit")}</span>
        <h3>${escapeHtml(item.nom)}</h3>
        <p>Qté ${item.quantite || 0} · Achat ${euro(item.prix_achete)}</p>
        <strong>${item.prix_marche ? euro(item.prix_marche) : "Prix indisponible"}</strong>
        <small>${item.price_status === "cached" ? "Dernier prix connu" : dateLabel(item.derniere_maj)}</small>
        ${item.price_source_url ? `<a class="source-link" href="${escapeHtml(item.price_source_url)}" target="_blank" rel="noreferrer">CardMarket</a>` : ""}
      </div>
      <div class="portfolio-actions">
        <button class="icon-btn" data-refresh-id="${escapeHtml(item.id)}" title="Rafraîchir">🔄</button>
        <button class="icon-btn" data-delete-id="${escapeHtml(item.id)}" title="Supprimer">🗑️</button>
      </div>
    </article>
  `).join("");
  document.querySelectorAll("[data-refresh-id]").forEach(button => {
    button.addEventListener("click", async () => {
      await api.updatePrice(button.dataset.refreshId);
      await loadPortfolio();
    });
  });
  document.querySelectorAll("[data-delete-id]").forEach(button => {
    button.addEventListener("click", async () => {
      await api.deleteItem(button.dataset.deleteId);
      await loadPortfolio();
    });
  });
}

async function refreshPortfolio() {
  for (const item of state.items) {
    await api.updatePrice(item.id).catch(() => null);
  }
  await loadPortfolio();
}

function slugLike(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}
