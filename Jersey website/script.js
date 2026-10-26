
const retroDuplicateTelegramNumbers = new Set([1, 2, 3, 4, 5, 7, 10, 15, 16, 17, 26, 29, 30, 31, 35]);

let products = [
  ...Array.from({ length: 35 }, (_, index) => {
    const number = index + 1;
    const isEnglandShirt = number === 8 || number === 19;
    const isSpainShirt = number === 23;
    const isNigeriaShirt = number === 32;
    const isNationalShirt = isEnglandShirt || isSpainShirt || isNigeriaShirt;

    return {
      id: `telegram-${String(number).padStart(2, "0")}`,
      sku: `DEJ-${String(number).padStart(4, "0")}`,
      name: isEnglandShirt
        ? `England National Team Shirt ${number === 8 ? "01" : "02"}`
        : isSpainShirt
          ? "Spain National Team Shirt 01"
          : isNigeriaShirt
            ? "Nigeria National Team Jersey"
            : `Club Jersey ${String(number).padStart(2, "0")}`,
      team: isEnglandShirt ? "England" : isSpainShirt ? "Spain" : isNigeriaShirt ? "Nigeria" : "Club selection",
      category: isNationalShirt ? "national" : "club",
      price: number === 6 || number === 9 ? 24000 : 18000,
      currency: "NGN",
      image: `images/jerseys/photo_${number}_2026-10-17_00-41-31.jpg`,
      isNewArrival: number >= 30 || isNationalShirt,
      source: "telegram-import"
    };
  }).filter((_, index) => !retroDuplicateTelegramNumbers.has(index + 1)),
  ...[
    { team: "Brazil", name: "Brazil National Team Away Jersey", number: 1 },
    { team: "France", name: "France National Team Jersey", number: 2 },
    { team: "Brazil", name: "Brazil National Team Home Jersey", number: 3 },
    { team: "Morocco", name: "Morocco National Team Away Jersey", number: 4 },
    { team: "Morocco", name: "Morocco National Team Home Jersey", number: 5 },
    { team: "Brazil", name: "Brazil National Team Jersey and Shorts Set", number: 6 },
    { team: "Germany", name: "Germany National Team Jersey", number: 7 },
    { team: "Argentina", name: "Argentina National Team Jersey", number: 8 },
    { team: "England", name: "England National Team Red Away Jersey", number: 9 },
    { team: "Italy", name: "Italy National Team Jersey", number: 10 }
  ].map(({ team, name, number }) => ({
    id: `national-new-${String(number).padStart(2, "0")}`,
    sku: `DEJ-NT-${String(number).padStart(4, "0")}`,
    name,
    team,
    category: "national",
    price: 18000,
    currency: "NGN",
    image: `images/jerseys/photo_${number}_2026-10-17_10-44-53.jpg`,
    isNewArrival: true,
    source: "user-upload"
  })),
  {
    id: "real-madrid-dark-green",
    sku: "DEJ-RM-GREEN-01",
    name: "Real Madrid Dark Green Jersey",
    team: "Real Madrid",
    category: "club",
    price: 18000,
    currency: "NGN",
    image: "images/real-madrid-jersey.jpg",
    isNewArrival: true,
    source: "user-upload"
  },
  ...Array.from({ length: 15 }, (_, index) => {
    const number = index + 1;
    return {
      id: `retro-${String(number).padStart(2, "0")}`,
      sku: `DEJ-RETRO-${String(number).padStart(4, "0")}`,
      name: `Retro Jersey ${String(number).padStart(2, "0")}`,
      team: "Retro collection",
      category: "club",
      price: 24000,
      currency: "NGN",
      image: `images/Retro jersey/photo_${number}_2026-10-22_21-11-39.jpg`,
      isNewArrival: false,
      source: "user-upload"
    };
  })
];

const badgeAddOnPrice = 3000;
const badgeOptions = [
  { value: "none", label: "No badge", price: 0 },
  { value: "premier-league", label: "Premier League badge", price: badgeAddOnPrice },
  { value: "champions-league", label: "Champions League badge", price: badgeAddOnPrice },
  { value: "custom", label: "Other/custom badge", price: badgeAddOnPrice }
];

const businessWhatsApp = "2348145315246";
const productGrid = document.getElementById("productGrid");
const CART_STORAGE_KEY = "dej-shopping-bag";
const FAVORITES_STORAGE_KEY = "dej-favorites";

function clearProductImageLoader(event, hasError = false) {
  const image = event.target;
  if (!(image instanceof HTMLImageElement) || !image.classList.contains("product-photo")) return;

  const imageContainer = image.closest(".product-image");
  if (!imageContainer) return;

  imageContainer.classList.remove("is-loading");
  imageContainer.classList.toggle("has-error", hasError);
  imageContainer.setAttribute("aria-busy", "false");
}

if (productGrid) {
  productGrid.addEventListener("load", event => clearProductImageLoader(event), true);
  productGrid.addEventListener("error", event => clearProductImageLoader(event, true), true);
}

function readStoredArray(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

let shoppingCart = readStoredArray(CART_STORAGE_KEY);
const favoriteIds = new Set(readStoredArray(FAVORITES_STORAGE_KEY));

function saveShoppingCart() {
  localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(shoppingCart));
}

function saveFavorites() {
  localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify([...favoriteIds]));
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[character]);
}

function formatPrice(price) {
  return "₦" + price.toLocaleString("en-NG");
}

function getPhotoOrder(product) {
  const originalPhoto = product.id.match(/^telegram-(\d+)$/);
  if (originalPhoto) return Number(originalPhoto[1]);

  const laterPhoto = product.id.match(/^national-new-(\d+)$/);
  if (laterPhoto) return 100 + Number(laterPhoto[1]);

  const retroPhoto = product.id.match(/^retro-(\d+)$/);
  if (retroPhoto) return 200 + Number(retroPhoto[1]);

  return 200;
}

function renderProducts(items) {
  if (!productGrid) return;

  productGrid.innerHTML = items.map(product => `
    <article class="product-card" data-category="${product.category}">
      <div class="product-image is-loading" aria-busy="true">
        <img class="product-photo" src="${product.image}" alt="${product.name}" loading="lazy">
        ${product.isNewArrival ? '<span class="arrival-label">New arrival</span>' : ""}
        <button class="favorite-toggle ${favoriteIds.has(product.id) ? "is-favorite" : ""}" type="button" data-favorite-id="${product.id}" aria-label="${favoriteIds.has(product.id) ? "Remove from" : "Add to"} favorites: ${product.name}" aria-pressed="${favoriteIds.has(product.id)}">${favoriteIds.has(product.id) ? "♥" : "♡"}</button>
      </div>
      <div class="product-info">
        <p class="catalog-number">JERSEY ${String(product.jerseyNumber).padStart(2, "0")}</p>
        <p>${product.team} · ${product.category === "national" ? "National team" : "Club"}</p>
        <h3>${product.name}</h3>
        <div class="product-price">${formatPrice(product.price)}</div>
        <button class="details-button" type="button" data-details-id="${product.id}">VIEW DETAILS</button>
        <label class="size-label" for="size-${product.id}">Size</label>
        ${product.stockTracked && product.availableSizes.length === 0
          ? '<p class="out-of-stock">Currently out of stock</p>'
          : `<select class="size-select" id="size-${product.id}" required>
              <option value="" selected disabled>Select size</option>
              ${(product.stockTracked ? product.availableSizes : ["S", "L", "XL", "XXL"]).map(size => `<option value="${size}">${size}</option>`).join("")}
            </select>`}
        ${product.category === "club" ? `
          <label class="badge-label" for="badge-${product.id}">Add a badge <span>+${formatPrice(badgeAddOnPrice)}</span></label>
          <select class="badge-select" id="badge-${product.id}" data-product-id="${product.id}">
            ${badgeOptions.map(option => `<option value="${option.value}" data-price="${option.price}">${option.label}${option.price ? ` (+${formatPrice(option.price)})` : ""}</option>`).join("")}
          </select>
          <input class="custom-badge-input" type="text" maxlength="60" placeholder="Tell us which badge" aria-label="Custom badge request for ${product.name}" hidden>
        ` : ""}
        <button class="btn add-to-cart-button" data-add-id="${product.id}" type="button" ${product.stockTracked && product.availableSizes.length === 0 ? "disabled" : ""}>ADD TO CART</button>
      </div>
    </article>
  `).join("");
}

function getBadgeForCard(card, product) {
  if (product.category !== "club") {
    return { value: "none", label: "No badge", price: 0, customText: "" };
  }

  const selection = card.querySelector(".badge-select");
  const option = badgeOptions.find(item => item.value === selection.value);
  return {
    ...option,
    customText: card.querySelector(".custom-badge-input").value.trim()
  };
}

function addProductToCart(product, card) {
  const size = card.querySelector(".size-select").value;
  if (!size) {
    card.querySelector(".size-select").reportValidity();
    return;
  }

  const badge = getBadgeForCard(card, product);
  if (badge.value === "custom" && !badge.customText) {
    alert("Please tell us which badge you want.");
    card.querySelector(".custom-badge-input").focus();
    return;
  }

  const key = [product.id, size, badge.value, badge.customText].join("::");
  const existing = shoppingCart.find(item => item.key === key);
  if (existing) {
    existing.quantity += 1;
  } else {
    shoppingCart.push({
      key,
      productId: product.id,
      size,
      badgeValue: badge.value,
      badgeLabel: badge.label,
      badgeCustomText: badge.customText,
      quantity: 1
    });
  }

  saveShoppingCart();
  renderShoppingCart();
  document.getElementById("cartDialog")?.showModal();
}

function openProductDetails(product) {
  const details = document.getElementById("productDetails");
  if (!details) return;

  details.innerHTML = `
    <div class="product-detail-layout">
      <img class="product-detail-image" src="${product.image}" alt="${escapeHtml(product.name)}">
      <div class="product-detail-copy">
        <p class="eyebrow">${product.category === "national" ? "NATIONAL TEAM" : "CLUB JERSEY"}</p>
        <h2 id="productDialogTitle">${escapeHtml(product.name)}</h2>
        <p class="product-detail-team">${escapeHtml(product.team)}</p>
        <strong class="product-detail-price">${formatPrice(product.price)}</strong>
        <dl class="product-detail-facts">
          <div><dt>Product code</dt><dd>${escapeHtml(product.sku)}</dd></div>
          <div><dt>Sizes shown</dt><dd>${product.stockTracked ? (product.availableSizes.join(", ") || "Currently out of stock") : "S, L, XL, XXL · availability confirmed after order"}</dd></div>
          <div><dt>Customization</dt><dd>${product.category === "club" ? "Club badge add-on available" : "No badge add-on for national jerseys"}</dd></div>
        </dl>
        <p class="help-note">Confirm current availability and delivery details with us before ordering.</p>
      </div>
    </div>
  `;
  document.getElementById("productDialog")?.showModal();
}

function getCartLinePrice(item) {
  const product = products.find(entry => entry.id === item.productId);
  if (!product) return 0;
  const badge = product.category === "club"
    ? badgeOptions.find(option => option.value === item.badgeValue)
    : null;
  return product.price + (badge?.price || 0);
}

function renderShoppingCart() {
  const container = document.getElementById("cartItems");
  const count = document.getElementById("cartCount");
  const totalElement = document.getElementById("cartTotal");
  const checkoutButtons = document.querySelectorAll("#checkoutDetails button[type='submit']");
  const clearButton = document.getElementById("clearCart");
  if (!container || !count || !totalElement || checkoutButtons.length === 0 || !clearButton) return;

  shoppingCart = shoppingCart.filter(item => products.some(product => product.id === item.productId));
  const itemCount = shoppingCart.reduce((sum, item) => sum + item.quantity, 0);
  const total = shoppingCart.reduce((sum, item) => sum + getCartLinePrice(item) * item.quantity, 0);
  count.textContent = String(itemCount);
  document.getElementById("cartOpen")?.setAttribute("aria-label", `Open cart, ${itemCount} ${itemCount === 1 ? "item" : "items"}`);
  totalElement.textContent = formatPrice(total);
  checkoutButtons.forEach(button => {
    button.disabled = shoppingCart.length === 0;
  });
  clearButton.disabled = shoppingCart.length === 0;

  if (shoppingCart.length === 0) {
    container.innerHTML = '<p class="empty-cart">Your cart is empty. Add a jersey to start an order.</p>';
    return;
  }

  container.innerHTML = shoppingCart.map(item => {
    const product = products.find(entry => entry.id === item.productId);
    const badgeLine = product.category === "club" && item.badgeValue !== "none"
      ? `<p>${escapeHtml(item.badgeLabel)}${item.badgeCustomText ? ` · ${escapeHtml(item.badgeCustomText)}` : ""}</p>`
      : "";
    return `
      <article class="cart-line">
        <img src="${product.image}" alt="" loading="lazy">
        <div class="cart-line-info">
          <h3>${escapeHtml(product.name)}</h3>
          <p>Size ${escapeHtml(item.size)}</p>
          ${badgeLine}
          <strong>${formatPrice(getCartLinePrice(item) * item.quantity)}</strong>
          <div class="quantity-control" aria-label="Quantity controls for ${escapeHtml(product.name)}">
            <button type="button" data-cart-action="decrease" data-cart-key="${escapeHtml(item.key)}" aria-label="Decrease quantity">−</button>
            <span>${item.quantity}</span>
            <button type="button" data-cart-action="increase" data-cart-key="${escapeHtml(item.key)}" aria-label="Increase quantity">+</button>
            <button class="remove-line" type="button" data-cart-action="remove" data-cart-key="${escapeHtml(item.key)}">Remove</button>
          </div>
        </div>
      </article>
    `;
  }).join("");
}

async function checkoutShoppingCart(event) {
  event.preventDefault();
  if (shoppingCart.length === 0) return;
  const form = event.currentTarget;
  if (!form.reportValidity()) return;

  const name = document.getElementById("checkoutName").value.trim();
  const phone = document.getElementById("checkoutPhone").value.trim();
  const address = document.getElementById("checkoutAddress").value.trim();
  const channel = event.submitter?.value === "email" ? "email" : "whatsapp";
  const destinationWindow = channel === "whatsapp" ? window.open("about:blank", "_blank") : null;

  const lines = shoppingCart.map((item, index) => {
    const product = products.find(entry => entry.id === item.productId);
    const badge = product.category !== "club"
      ? "Not applicable for national-team jerseys"
      : item.badgeValue === "none"
        ? "No badge"
        : `${item.badgeLabel}${item.badgeCustomText ? ` - ${item.badgeCustomText}` : ""}`;
    return `ITEM ${String(index + 1).padStart(2, "0")}\n${product.name}\nTeam: ${product.team}\nProduct code: ${product.sku}\nSize: ${item.size}\nBadge: ${badge}\nQuantity: ${item.quantity}\nLine total: ${formatPrice(getCartLinePrice(item) * item.quantity)}`;
  });
  const total = shoppingCart.reduce((sum, item) => sum + getCartLinePrice(item) * item.quantity, 0);
  let orderReference = "";
  if (window.location.protocol !== "file:") {
    try {
      const response = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          phone: phone.trim(),
          address: address.trim(),
          items: shoppingCart.map(item => ({
            product_id: item.productId,
            size: item.size,
            quantity: item.quantity,
            badge: item.badgeValue,
            custom_text: item.badgeCustomText
          }))
        })
      });
      const result = await response.json();
      if (!response.ok && response.status < 500) {
        destinationWindow?.close();
        alert(result.error || "The order request could not be saved. Please review your cart.");
        return;
      }
      if (response.ok) orderReference = result.reference || "";
    } catch {
      orderReference = "";
    }
  }

  const message = `
DESMOND EMPIRE JERSEYS
NEW ORDER REQUEST
========================================

${orderReference ? `Order reference: ${orderReference}\n` : ""}CUSTOMER DETAILS
Name: ${name.trim()}
Phone: ${phone.trim()}
Delivery address: ${address.trim()}

ORDER ITEMS
----------------------------------------
${lines.join("\n\n")}

Estimated subtotal (delivery not included): ${formatPrice(total)}

NEXT STEP
Please confirm stock, delivery fee, and final total with the customer. No payment has been made.

Thank you,
Desmond Empire Jerseys
  `.trim();

  if (channel === "email") {
    const subject = `Desmond Empire Jerseys - Order request${orderReference ? ` ${orderReference}` : ""}`;
    document.getElementById("emailOrderSubject").value = subject;
    document.getElementById("emailOrderBody").value = message;
    document.getElementById("openEmailApp").href =
      `mailto:Nifemidesmond28@gmail.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(message)}`;
    document.getElementById("emailCopyStatus").textContent =
      "Opening your email app creates a draft. You still need to send it.";
    document.getElementById("emailDraftDialog")?.showModal();
    return;
  }

  const destination = `https://wa.me/${businessWhatsApp}?text=${encodeURIComponent(message)}`;

  if (destinationWindow && !destinationWindow.closed) {
    destinationWindow.location.href = destination;
  } else {
    window.location.href = destination;
  }
}

if (productGrid) {
  let activeFilter = "all";
  let activeQuery = "";

  function updateProductList() {
    const numberedProducts = [...products]
      .sort((first, second) => getPhotoOrder(first) - getPhotoOrder(second))
      .map((product, index) => {
        const namedNumber = product.name.match(/(\d+)$/);
        return {
          ...product,
          catalogNumber: index + 1,
          jerseyNumber: namedNumber ? Number(namedNumber[1]) : index + 1
        };
      });
    const exactCatalogNumber = activeQuery.match(/^jersey\s+0*(\d+)$/);
    const filtered = numberedProducts.filter(product => {
      const matchesFilter = activeFilter === "all" ||
        (activeFilter === "new"
          ? product.isNewArrival
          : activeFilter === "favorites"
            ? favoriteIds.has(product.id)
            : product.category === activeFilter);
      const searchText = `jersey ${String(product.jerseyNumber).padStart(2, "0")} ${product.name} ${product.team} ${product.sku}`.toLowerCase();
          const matchesQuery = exactCatalogNumber
        ? product.jerseyNumber === Number(exactCatalogNumber[1])
            : searchText.includes(activeQuery);
          return matchesFilter && matchesQuery;
    });
    renderProducts(filtered);
    const status = document.getElementById("searchStatus");
    if (status) status.textContent = filtered.length ? `${filtered.length} jerseys shown.` : "No jerseys found. Try another search.";
  }

  updateProductList();

  productGrid.addEventListener("click", event => {
    const favoriteButton = event.target.closest(".favorite-toggle");
    if (favoriteButton) {
      const product = products.find(item => item.id === favoriteButton.dataset.favoriteId);
      if (!product) return;
      if (favoriteIds.has(product.id)) favoriteIds.delete(product.id);
      else favoriteIds.add(product.id);
      saveFavorites();
      if (activeFilter === "favorites") updateProductList();
      else {
        const isFavorite = favoriteIds.has(product.id);
        favoriteButton.classList.toggle("is-favorite", isFavorite);
        favoriteButton.setAttribute("aria-pressed", String(isFavorite));
        favoriteButton.setAttribute("aria-label", `${isFavorite ? "Remove from" : "Add to"} favorites: ${product.name}`);
        favoriteButton.textContent = isFavorite ? "♥" : "♡";
      }
      return;
    }

    const detailsButton = event.target.closest(".details-button");
    if (detailsButton) {
      const product = products.find(item => item.id === detailsButton.dataset.detailsId);
      if (product) openProductDetails(product);
      return;
    }

    const addButton = event.target.closest(".add-to-cart-button");
    if (!addButton) return;
    const product = products.find(item => item.id === addButton.dataset.addId);
    if (product) addProductToCart(product, addButton.closest(".product-card"));
  });

  productGrid.addEventListener("change", event => {
    if (!event.target.matches(".badge-select")) return;
    const customInput = event.target.closest(".product-info").querySelector(".custom-badge-input");
    customInput.hidden = event.target.value !== "custom";
  });

  document.querySelectorAll(".filter-button").forEach(button => {
    button.addEventListener("click", () => {
      activeFilter = button.dataset.filter;
      document.querySelectorAll(".filter-button").forEach(filterButton => {
        const isActive = filterButton === button;
        filterButton.classList.toggle("is-active", isActive);
        filterButton.setAttribute("aria-pressed", String(isActive));
      });
      updateProductList();
    });
  });

  const searchInput = document.getElementById("jerseySearch");
  searchInput?.addEventListener("input", () => {
    activeQuery = searchInput.value.trim().toLowerCase();
    updateProductList();
  });

  async function loadLiveCatalog() {
    if (window.location.protocol === "file:") return;
    try {
      const response = await fetch("/api/products");
      if (!response.ok) return;
      const liveProducts = await response.json();
      if (!Array.isArray(liveProducts)) return;
      products = liveProducts;
      updateProductList();
      renderShoppingCart();
    } catch {
      // Keep the embedded catalog available when the API is not reachable.
    }
  }

  loadLiveCatalog();
}

renderShoppingCart();

document.getElementById("cartOpen")?.addEventListener("click", () => {
  document.getElementById("cartDialog")?.showModal();
});

document.getElementById("cartItems")?.addEventListener("click", event => {
  const button = event.target.closest("[data-cart-action]");
  if (!button) return;

  const item = shoppingCart.find(entry => entry.key === button.dataset.cartKey);
  if (!item) return;
  if (button.dataset.cartAction === "remove") {
    shoppingCart = shoppingCart.filter(entry => entry.key !== item.key);
  } else if (button.dataset.cartAction === "increase") {
    item.quantity = Math.min(item.quantity + 1, 100);
  } else if (button.dataset.cartAction === "decrease") {
    item.quantity -= 1;
    if (item.quantity < 1) shoppingCart = shoppingCart.filter(entry => entry.key !== item.key);
  }

  saveShoppingCart();
  renderShoppingCart();
});

document.getElementById("checkoutDetails")?.addEventListener("submit", checkoutShoppingCart);
document.getElementById("clearCart")?.addEventListener("click", () => {
  if (shoppingCart.length === 0 || !window.confirm("Remove every item from your cart?")) return;
  shoppingCart = [];
  saveShoppingCart();
  renderShoppingCart();
});

document.getElementById("copyEmailDraft")?.addEventListener("click", async () => {
  const subject = document.getElementById("emailOrderSubject").value;
  const body = document.getElementById("emailOrderBody").value;
  const copyText = `To: Nifemidesmond28@gmail.com\nSubject: ${subject}\n\n${body}`;
  const status = document.getElementById("emailCopyStatus");
  try {
    await navigator.clipboard.writeText(copyText);
  } catch {
    const bodyField = document.getElementById("emailOrderBody");
    bodyField.focus();
    bodyField.select();
    document.execCommand("copy");
  }
  status.textContent = "Order details copied. Paste them into an email to send.";
});
document.querySelectorAll("[data-close-dialog]").forEach(button => {
  button.addEventListener("click", () => button.closest("dialog")?.close());
});

const searchForm = document.getElementById("searchForm");
if (searchForm) {
  searchForm.addEventListener("submit", event => event.preventDefault());
}

const themeToggle = document.getElementById("themeToggle");
const themePicker = themeToggle?.closest(".theme-picker");
const themeInputs = themePicker?.querySelectorAll('input[name="themeMode"]') ?? [];
const themeIcons = { light: "☀", dark: "☾", system: "▣" };
const themeNames = { light: "Light", dark: "Dark", system: "System" };
const systemThemePreference = window.matchMedia("(prefers-color-scheme: light)");
let selectedTheme = localStorage.getItem("dej-theme");
if (!Object.hasOwn(themeIcons, selectedTheme)) selectedTheme = "system";

function applyTheme(mode, savePreference = true) {
  selectedTheme = mode;
  const resolvedTheme = mode === "system" ? (systemThemePreference.matches ? "light" : "dark") : mode;
  document.documentElement.dataset.theme = resolvedTheme;
  document.documentElement.dataset.themeMode = mode;
  if (savePreference) localStorage.setItem("dej-theme", mode);

  if (!themeToggle) return;
  const themeName = themeNames[mode];
  themeToggle.setAttribute("aria-label", `Color theme: ${themeName}`);
  themeToggle.title = `Color theme: ${themeName}`;
  themeToggle.querySelector(".theme-icon").textContent = themeIcons[mode];
  themeToggle.querySelector(".theme-label").textContent = themeName;
  themeInputs.forEach(input => { input.checked = input.value === mode; });
}

applyTheme(selectedTheme, false);
themePicker?.addEventListener("change", event => {
  if (!event.target.matches('input[name="themeMode"]')) return;
  applyTheme(event.target.value);
  themePicker.open = false;
  themeToggle.focus();
});
document.addEventListener("click", event => {
  if (themePicker && !themePicker.contains(event.target)) themePicker.open = false;
});
systemThemePreference.addEventListener("change", () => {
  if (selectedTheme === "system") applyTheme("system", false);
});

const menuToggle = document.getElementById("menuToggle");
const navMenu = document.getElementById("navMenu");
menuToggle?.addEventListener("click", () => {
  const isOpen = navMenu.classList.toggle("open");
  menuToggle.setAttribute("aria-expanded", String(isOpen));
});
navMenu?.querySelectorAll("a").forEach(link => {
  link.addEventListener("click", () => {
    navMenu.classList.remove("open");
    menuToggle?.setAttribute("aria-expanded", "false");
  });
});

const year = document.getElementById("year");
if (year) year.textContent = new Date().getFullYear();
