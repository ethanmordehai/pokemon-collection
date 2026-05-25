const api = {
  async collection(collectionId = "") {
    const params = collectionId ? `?collection_id=${encodeURIComponent(collectionId)}` : "";
    return requestJson(`/api/collection${params}`);
  },

  async createCollection(name) {
    return requestJson("/api/collections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
  },

  async addItem(payload, collectionId = "") {
    if (collectionId) payload.collection_id = collectionId;
    return requestJson("/api/collection/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },

  async updateItem(id, payload, collectionId = "") {
    if (collectionId) payload.collection_id = collectionId;
    return requestJson(`/api/collection/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },

  async deleteItem(id, collectionId = "") {
    const params = collectionId ? `?collection_id=${encodeURIComponent(collectionId)}` : "";
    return requestJson(`/api/collection/${id}${params}`, { method: "DELETE" });
  },

  async updatePrice(id) {
    return requestJson(`/api/price/${id}`);
  },

  async updateAllPrices() {
    return requestJson("/api/price/update_all", { method: "POST" });
  },

  async searchProduct(query, category = "") {
    const params = new URLSearchParams({ q: query });
    if (category) params.set("category", category);
    return requestJson(`/api/search_product?${params.toString()}`);
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
