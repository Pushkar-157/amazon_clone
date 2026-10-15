// Cart page: change quantities, remove items, enter an address and place the order.
(function () {
  const { useState, useEffect } = React;

  function CartView() {
    const [cart, setCart] = useState(null);
    const [user, setUser] = useState(undefined); // undefined = still loading
    const [address, setAddress] = useState("");
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState(false);

    useEffect(() => {
      api.get("/api/cart").then(setCart).catch((e) => setError(e.message));
      api.get("/api/me").then((d) => setUser(d.user)).catch(() => setUser(null));
    }, []);

    async function update(call) {
      setError(null);
      try {
        const next = await call();
        setCart(next);
        emitCart(next);
      } catch (e) {
        setError(e.message);
      }
    }

    const changeQty = (id, qty) => update(() => api.patch("/api/cart/items/" + id, { quantity: qty }));
    const remove = (id) => update(() => api.del("/api/cart/items/" + id));

    async function placeOrder() {
      setBusy(true);
      setError(null);
      try {
        const order = await api.post("/api/checkout", { shipping_address: address });
        emitCart({ count: 0 });
        window.location.href = "/orders?placed=" + order.id;
      } catch (e) {
        setError(e.message);
        setBusy(false);
      }
    }

    if (!cart) return error ? <p className="msg err">{error}</p> : <p className="muted">Loading your cart…</p>;

    if (cart.items.length === 0) {
      return (
        <div className="empty">
          <p>Your cart is empty.</p>
          <a className="btn" href="/">Find something to buy</a>
        </div>
      );
    }

    return (
      <div className="cart-layout">
        <section>
          {cart.items.map(({ product, quantity, subtotal }) => (
            <div className="card cart-row" key={product.id}>
              <a href={"/product/" + product.id} className="thumb small">
                {product.image_url
                  ? <img src={product.image_url} alt={product.name} />
                  : <span className="icon" aria-hidden="true">{product.icon}</span>}
              </a>
              <div className="cart-info">
                <a href={"/product/" + product.id} className="title">{product.name}</a>
                <div className="muted">{formatPrice(product.price)} each</div>
                <div className="qty">
                  <button className="btn secondary" aria-label={"Decrease " + product.name}
                          disabled={quantity <= 1} onClick={() => changeQty(product.id, quantity - 1)}>−</button>
                  <span>{quantity}</span>
                  <button className="btn secondary" aria-label={"Increase " + product.name}
                          disabled={quantity >= product.stock} onClick={() => changeQty(product.id, quantity + 1)}>+</button>
                  <button className="linklike" onClick={() => remove(product.id)}>Remove</button>
                </div>
              </div>
              <div className="price">{formatPrice(subtotal)}</div>
            </div>
          ))}
        </section>

        <aside className="card summary">
          <h2>Order summary</h2>
          <p className="total-line"><span>Items ({cart.count})</span><strong>{formatPrice(cart.total)}</strong></p>

          {user === null && (
            <p>
              <a className="btn wide" href="/login?next=/cart">Sign in to check out</a>
            </p>
          )}

          {user && (
            <div>
              <label htmlFor="address">Shipping address</label>
              <textarea id="address" rows="3" value={address} maxLength="255"
                        placeholder="House number, street, city, PIN code"
                        onChange={(e) => setAddress(e.target.value)} />
              <button className="btn wide" onClick={placeOrder} disabled={busy}>
                {busy ? "Placing order…" : "Place order"}
              </button>
            </div>
          )}

          {error && <p className="msg err" role="alert">{error}</p>}
        </aside>
      </div>
    );
  }

  const root = document.getElementById("cart-root");
  if (root) ReactDOM.createRoot(root).render(<CartView />);
})();
