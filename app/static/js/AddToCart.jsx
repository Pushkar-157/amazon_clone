// Quantity picker and "Add to cart" button on the product page.
(function () {
  const { useState } = React;

  function AddToCart({ productId, stock }) {
    const [qty, setQty] = useState(1);
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState(null);

    if (stock < 1) {
      return <p className="muted">This item can't be added to the cart right now.</p>;
    }

    const options = Array.from({ length: Math.min(stock, 10) }, (_, i) => i + 1);

    async function add() {
      setBusy(true);
      setMessage(null);
      try {
        const cart = await api.post("/api/cart/items", { product_id: productId, quantity: qty });
        emitCart(cart);
        setMessage({ ok: true, text: "Added to your cart." });
      } catch (error) {
        setMessage({ ok: false, text: error.message });
      }
      setBusy(false);
    }

    return (
      <div className="add-to-cart">
        <label>
          Quantity{" "}
          <select value={qty} onChange={(e) => setQty(Number(e.target.value))}>
            {options.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
        <button className="btn" onClick={add} disabled={busy}>Add to cart</button>
        {message && (
          <p className={message.ok ? "msg ok" : "msg err"} role="status">
            {message.text} {message.ok && <a href="/cart">View cart</a>}
          </p>
        )}
      </div>
    );
  }

  const root = document.getElementById("add-to-cart-root");
  if (root) {
    ReactDOM.createRoot(root).render(
      <AddToCart productId={Number(root.dataset.productId)} stock={Number(root.dataset.stock)} />
    );
  }
})();
