const api = {
  async collection() {
    return requestJson("/api/collection");
  },

  async addItem(payload) {
    return requestJson("/api/collection/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },

  async updateItem(id, payload) {
    return requestJson(`/api/collection/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },

  async deleteItem(id) {
    return requestJson(`/api/collection/${id}`, { method: "DELETE" });
  },

  async updatePrice(id) {
    return requestJson(`/api/price/${id}`);
  },

  async updateAllPrices() {
    return requestJson("/api/price/update_all", { method: "POST" });
  },

  async searchProduct(query) {
    return requestJson(`/api/search_product?q=${encodeURIComponent(query)}`);
  },

  async news() {
    return requestJson("/api/news");
  },
};

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Requête impossible");
  }
  return payload;
}

function euro(value) {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(Number(value || 0));
}

function dateLabel(value) {
  if (!value) return "Jamais";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
