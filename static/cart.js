(() => {
  "use strict";
  const buttons = [...document.querySelectorAll(".add")];
  if (buttons.length === 0) return;
  const names = new Map(buttons.map(button => [button.dataset.sku, button.dataset.name]));
  const cart = new Map();
  const items = document.querySelector("#cart-items");
  const summary = document.querySelector("#cart-summary");
  const country = document.querySelector("#destination");
  const output = document.querySelector("#preview-result");
  const preview = document.querySelector("#preview");
  const key = "supreme-cart-v1";
  let requestId = 0;
  try {
    const saved = JSON.parse(localStorage.getItem(key) || "[]");
    if (Array.isArray(saved)) for (const entry of saved.slice(0, 25)) {
      if (!Array.isArray(entry)) continue;
      const [sku, quantity] = entry;
      if (names.has(sku) && Number.isInteger(quantity) && quantity >= 1 && quantity <= 20) cart.set(sku, quantity);
    }
  } catch { /* The cart still works without browser storage. */ }

  try {
    const labels = new Intl.DisplayNames([document.documentElement.lang || "en"], {type: "region"});
    for (const option of country.options) if (option.value) option.textContent = labels.of(option.value);
  } catch { /* Fall back to the configured country codes. */ }

  function invalidate() {
    requestId += 1;
    output.textContent = "";
    preview.disabled = cart.size === 0;
  }
  function render(focusSku = null) {
    invalidate();
    const count = [...cart.values()].reduce((total, value) => total + value, 0);
    summary.textContent = count ? (count === 1 ? "1 item" : count + " items") : "Your cart is empty.";
    items.replaceChildren();
    let focus = null;
    for (const [sku, quantity] of cart) {
      const li = document.createElement("li");
      li.append(document.createTextNode(names.get(sku) + " × " + quantity + " "));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Remove one";
      remove.setAttribute("aria-label", "Remove one " + names.get(sku));
      remove.addEventListener("click", () => {
        if (quantity === 1) cart.delete(sku);
        else cart.set(sku, quantity - 1);
        render(sku);
      });
      li.append(remove);
      items.append(li);
      if (sku === focusSku) focus = remove;
    }
    if (focusSku) (focus || buttons.find(button => button.dataset.sku === focusSku))?.focus();
    try { localStorage.setItem(key, JSON.stringify([...cart])); } catch { /* Optional persistence. */ }
  }
  for (const button of buttons) button.addEventListener("click", () => {
    const sku = button.dataset.sku;
    const quantity = cart.get(sku) || 0;
    if (quantity >= 20 || (!quantity && cart.size >= 25)) {
      output.textContent = "Cart limit reached: up to 25 products and 20 units per product.";
      return;
    }
    cart.set(sku, quantity + 1);
    render();
  });
  country.addEventListener("change", invalidate);
  preview.addEventListener("click", async () => {
    if (!country.value) {
      output.textContent = "Select a delivery country.";
      country.focus();
      return;
    }
    const current = ++requestId;
    preview.disabled = true;
    output.textContent = "Checking shipping…";
    try {
      const response = await fetch("/api/cart/preview", {
        method: "POST", headers: {"Content-Type": "application/json"}, credentials: "same-origin",
        body: JSON.stringify({country: country.value, items: [...cart].map(([sku, quantity]) => ({sku, quantity}))}),
      });
      const result = await response.json();
      if (current !== requestId) return;
      output.textContent = response.ok
        ? "Ships to this country. Product subtotal: " + result.subtotal + ". Shipping, taxes and duties are not included."
        : (result.error || "Shipping check failed.") + (result.unavailable?.length ? " " + result.unavailable.join(", ") + "." : "");
    } catch {
      if (current === requestId) output.textContent = "Could not check shipping. Try again.";
    } finally {
      if (current === requestId) preview.disabled = false;
    }
  });
  render();
})();
