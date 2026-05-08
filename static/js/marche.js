let marketLoaded = false;

async function loadMarket() {
  const newsGrid = document.querySelector("#newsGrid");
  const trendUp = document.querySelector("#trendUp");
  const trendDown = document.querySelector("#trendDown");
  newsGrid.innerHTML = `<article class="news-card"><div class="news-placeholder"></div><div class="news-body"><h2>Chargement du marché...</h2><p>Récupération des sources TCG.</p></div></article>`;

  try {
    const payload = await api.news();
    marketLoaded = true;
    newsGrid.innerHTML = payload.articles.map(renderNewsCard).join("");
    trendUp.innerHTML = renderTrendList(payload.trends.up, true);
    trendDown.innerHTML = renderTrendList(payload.trends.down, false);
  } catch (error) {
    newsGrid.innerHTML = `<article class="news-card"><div class="news-placeholder"></div><div class="news-body"><h2>Marché indisponible</h2><p>${escapeHtml(error.message)}</p></div></article>`;
  }
}

function renderNewsCard(article) {
  const image = article.image
    ? `<img src="${escapeHtml(article.image)}" alt="">`
    : `<div class="news-placeholder"></div>`;
  return `
    <article class="news-card">
      ${image}
      <div class="news-body">
        <h2>${escapeHtml(article.title)}</h2>
        <p>${escapeHtml(article.summary || "Résumé indisponible pour cette source.")}</p>
        <div class="tag-row">${(article.tags || []).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
        <small>${escapeHtml(article.source)} · ${escapeHtml(article.date || "Date inconnue")}</small><br>
        <a class="read-more" href="${escapeHtml(article.url)}" target="_blank" rel="noreferrer">Lire la suite</a>
      </div>
    </article>
  `;
}

function renderTrendList(items, upward) {
  if (!items || !items.length) {
    return `<p class="muted">Lance une mise à jour des prix pour alimenter cette tendance.</p>`;
  }
  return items.map(item => `
    <div class="trend-item">
      <span>${escapeHtml(item.nom)}</span>
      <strong class="${upward ? "positive" : "negative"}">${Number(item.variation_pct || 0).toFixed(1)}%</strong>
    </div>
  `).join("");
}
