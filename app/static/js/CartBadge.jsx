// Shows the number of items in the cart, next to the "Cart" link in the header.
(function () {
  const { useState, useEffect } = React;

  function CartBadge() {
    const [count, setCount] = useState(0);

    useEffect(() => {
      api.get("/api/cart").then((cart) => setCount(cart.count)).catch(() => {});
      const onUpdate = (event) => setCount(event.detail.count);
      window.addEventListener("cart:updated", onUpdate);
      return () => window.removeEventListener("cart:updated", onUpdate);
    }, []);

    return <span className="badge" aria-label={count + " items in cart"}>{count}</span>;
  }

  const root = document.getElementById("cart-badge-root");
  if (root) ReactDOM.createRoot(root).render(<CartBadge />);
})();
