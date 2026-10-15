// Small helpers shared by every React component.
// Loaded as a normal script, so everything is attached to `window`.

window.api = {
  async request(method, url, body) {
    const options = { method, headers: {}, credentials: "same-origin" };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    const response = await fetch(url, options);
    let data = null;
    if (response.status !== 204) {
      try { data = await response.json(); } catch (e) { /* not JSON */ }
    }
    if (!response.ok) {
      const error = new Error((data && data.error) || "Something went wrong. Please try again.");
      error.status = response.status;
      throw error;
    }
    return data;
  },
  get(url) { return this.request("GET", url); },
  post(url, body) { return this.request("POST", url, body || {}); },
  patch(url, body) { return this.request("PATCH", url, body || {}); },
  del(url) { return this.request("DELETE", url); },
};

window.formatPrice = function (value) {
  return "₹" + Number(value).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

// Tell the cart badge in the header that the cart changed.
window.emitCart = function (cart) {
  window.dispatchEvent(new CustomEvent("cart:updated", { detail: { count: cart.count } }));
};
