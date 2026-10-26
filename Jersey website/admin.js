const adminTokenKey = "dej-admin-token";
const adminLoginSection = document.getElementById("adminLoginSection");
const adminDashboard = document.getElementById("adminDashboard");
const adminMessage = document.getElementById("adminMessage");
const dashboardMessage = document.getElementById("dashboardMessage");

function escapeAdminHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[character]);
}

async function adminRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": sessionStorage.getItem(adminTokenKey) || "",
      ...options.headers
    }
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status}).`);
  return result;
}

async function loadAdminData() {
  dashboardMessage.textContent = "Loading store data...";
  try {
    const [products, orders] = await Promise.all([
      adminRequest("/api/admin/products"),
      adminRequest("/api/admin/orders")
    ]);
    renderInventory(products);
    renderOrders(orders);
    adminLoginSection.hidden = true;
    adminDashboard.hidden = false;
    dashboardMessage.textContent = "Store data loaded.";
  } catch (error) {
    sessionStorage.removeItem(adminTokenKey);
    adminLoginSection.hidden = false;
    adminDashboard.hidden = true;
    adminMessage.textContent = error.message;
  }
}

function renderInventory(products) {
  document.getElementById("inventoryList").innerHTML = products.map(product => `
    <details class="admin-product ${product.isActive ? "" : "is-archived"}" data-product-id="${escapeAdminHtml(product.id)}">
      <summary>
        <span class="admin-product-identity"><strong>${escapeAdminHtml(product.name)}</strong><small>${escapeAdminHtml(product.sku)} · ${escapeAdminHtml(product.team)}</small></span>
        <span class="admin-product-state ${product.isActive ? "is-available" : "is-archived-label"}">${product.isActive ? "On sale" : "Archived"}</span>
      </summary>
      <div class="admin-product-body">
        <div class="admin-product-meta"><span>${product.category === "national" ? "National team" : "Club"}</span><strong>₦${Number(product.price).toLocaleString("en-NG")}</strong></div>
        <div class="stock-inputs">
          ${["S", "L", "XL", "XXL"].map(size => `
            <label>${size}<input type="number" min="0" step="1" data-stock-size="${size}" value="${product.stockBySize[size] ?? ""}" placeholder="Untracked"></label>
          `).join("")}
        </div>
        <div class="admin-product-actions">
          <button class="btn save-stock-button" type="button">SAVE STOCK</button>
          <button class="text-button toggle-availability-button" type="button" data-active="${product.isActive}">${product.isActive ? "ARCHIVE JERSEY" : "RESTORE TO SHOP"}</button>
        </div>
      </div>
    </details>
  `).join("");
}

function renderOrders(orders) {
  const container = document.getElementById("ordersList");
  if (!orders.length) {
    container.innerHTML = '<p class="admin-help">No order requests have been recorded yet.</p>';
    return;
  }

  container.innerHTML = orders.map(order => `
    <details class="admin-order" data-order-reference="${escapeAdminHtml(order.reference)}">
      <summary>
        <span><strong>${escapeAdminHtml(order.reference)}</strong><small>${escapeAdminHtml(order.customer_name)} · ${new Date(order.created_at).toLocaleString()}</small></span>
        <span class="order-status">${escapeAdminHtml(order.status.replaceAll("_", " "))}</span>
      </summary>
      <div class="admin-order-body">
        <p>${escapeAdminHtml(order.customer_phone)}</p>
        <p>${escapeAdminHtml(order.delivery_address)}</p>
        <ul>${order.items.map(item => `<li>${escapeAdminHtml(item.product_name)} · ${escapeAdminHtml(item.size)} × ${item.quantity}${item.badge !== "none" ? ` · ${escapeAdminHtml(item.badge)}${item.badge_text ? ` (${escapeAdminHtml(item.badge_text)})` : ""}` : ""}</li>`).join("")}</ul>
        <strong>Subtotal: ₦${Number(order.subtotal).toLocaleString("en-NG")}</strong>
        <div class="order-status-controls">
          <label for="status-${escapeAdminHtml(order.reference)}">Update status</label>
          <select id="status-${escapeAdminHtml(order.reference)}" class="order-status-select">
            ${["pending_confirmation", "confirmed", "dispatched", "completed", "cancelled"].map(status => `<option value="${status}" ${order.status === status ? "selected" : ""}>${status.replaceAll("_", " ")}</option>`).join("")}
          </select>
          <button class="btn save-order-button" type="button">UPDATE</button>
        </div>
      </div>
    </details>
  `).join("");
}

document.getElementById("adminLoginForm").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const submitButton = form.querySelector("button[type='submit']");
  const message = document.getElementById("adminMessage");
  submitButton.disabled = true;
  message.textContent = "Signing in...";
  try {
    const response = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: form.elements.username.value
      })
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "Sign-in failed.");
    sessionStorage.setItem(adminTokenKey, result.token);
    message.textContent = "Signed in.";
    await loadAdminData();
  } catch (error) {
    sessionStorage.removeItem(adminTokenKey);
    message.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
});

document.getElementById("adminSignOut").addEventListener("click", () => {
  sessionStorage.removeItem(adminTokenKey);
  adminDashboard.hidden = true;
  adminLoginSection.hidden = false;
  adminMessage.textContent = "Signed out.";
});

document.getElementById("refreshAdmin").addEventListener("click", loadAdminData);

const addProductForm = document.getElementById("addProductForm");
const productImageInput = document.getElementById("productImage");
const productImagePreview = document.getElementById("productImagePreview");
const productImagePrompt = document.getElementById("productImagePrompt");
const addProductMessage = document.getElementById("addProductMessage");
let productImagePreviewUrl = "";

productImageInput.addEventListener("change", () => {
  if (productImagePreviewUrl) URL.revokeObjectURL(productImagePreviewUrl);
  const [file] = productImageInput.files;
  if (!file) {
    productImagePreview.hidden = true;
    productImagePrompt.hidden = false;
    return;
  }

  if (file.size > 5 * 1024 * 1024) {
    addProductMessage.textContent = "Choose an image smaller than 5 MB.";
    productImageInput.value = "";
    return;
  }

  productImagePreviewUrl = URL.createObjectURL(file);
  productImagePreview.src = productImagePreviewUrl;
  productImagePreview.hidden = false;
  productImagePrompt.hidden = true;
  addProductMessage.textContent = "";
});

addProductForm.addEventListener("submit", async event => {
  event.preventDefault();
  addProductMessage.textContent = "Adding jersey...";
  const submitButton = addProductForm.querySelector("button[type='submit']");
  submitButton.disabled = true;

  const formData = new FormData(addProductForm);
  formData.set("isNewArrival", String(addProductForm.elements.isNewArrival.checked));
  try {
    const response = await fetch("/api/admin/products", {
      method: "POST",
      headers: { "X-Admin-Token": sessionStorage.getItem(adminTokenKey) || "" },
      body: formData
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `Request failed (${response.status}).`);
    addProductForm.reset();
    productImagePreview.hidden = true;
    productImagePrompt.hidden = false;
    if (productImagePreviewUrl) URL.revokeObjectURL(productImagePreviewUrl);
    productImagePreviewUrl = "";
    document.getElementById("addProductPanel").open = false;
    await loadAdminData();
    dashboardMessage.textContent = `${result.name} is now in the shop.`;
    addProductMessage.textContent = "Jersey added and published.";
  } catch (error) {
    addProductMessage.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
});

document.getElementById("inventoryList").addEventListener("click", async event => {
  const availabilityButton = event.target.closest(".toggle-availability-button");
  if (availabilityButton) {
    const product = availabilityButton.closest(".admin-product");
    const isActive = availabilityButton.dataset.active === "true";
    availabilityButton.disabled = true;
    try {
      await adminRequest(`/api/admin/products/${encodeURIComponent(product.dataset.productId)}/availability`, {
        method: "PATCH",
        body: JSON.stringify({ isActive: !isActive })
      });
      await loadAdminData();
      dashboardMessage.textContent = isActive ? "Jersey archived from the public shop." : "Jersey restored to the public shop.";
    } catch (error) {
      dashboardMessage.textContent = error.message;
      availabilityButton.disabled = false;
    }
    return;
  }

  const button = event.target.closest(".save-stock-button");
  if (!button) return;
  const product = button.closest(".admin-product");
  const stock = {};
  for (const input of product.querySelectorAll("[data-stock-size]")) {
    const value = input.value.trim();
    if (value && (!Number.isInteger(Number(value)) || Number(value) < 0)) {
      dashboardMessage.textContent = "Stock must be a whole number of 0 or more, or left blank.";
      input.focus();
      return;
    }
    stock[input.dataset.stockSize] = value === "" ? null : Number(value);
  }

  button.disabled = true;
  try {
    await adminRequest(`/api/admin/products/${encodeURIComponent(product.dataset.productId)}/stock`, {
      method: "PATCH",
      body: JSON.stringify({ stock })
    });
    dashboardMessage.textContent = "Stock saved.";
    await loadAdminData();
  } catch (error) {
    dashboardMessage.textContent = error.message;
    button.disabled = false;
  }
});

document.getElementById("ordersList").addEventListener("click", async event => {
  const button = event.target.closest(".save-order-button");
  if (!button) return;
  const order = button.closest(".admin-order");
  const status = order.querySelector(".order-status-select").value;
  button.disabled = true;
  try {
    await adminRequest(`/api/admin/orders/${encodeURIComponent(order.dataset.orderReference)}`, {
      method: "PATCH",
      body: JSON.stringify({ status })
    });
    dashboardMessage.textContent = "Order status updated.";
    await loadAdminData();
  } catch (error) {
    dashboardMessage.textContent = error.message;
    button.disabled = false;
  }
});

if (sessionStorage.getItem(adminTokenKey)) loadAdminData();