// Home page: category filter, sorting, product grid and pagination.
// The search box lives in the header and reloads the page with ?q=...
(function () {
  const { useState, useEffect } = React;

  function ProductCard({ product, busy, onAdd }) {
    const link = "/product/" + product.id;
    const stockText =
      product.stock === 0 ? "Out of stock" :
      product.stock <= 5 ? "Only " + product.stock + " left" : "In stock";
    const stockClass = product.stock === 0 ? "out" : product.stock <= 5 ? "low" : "in";

    return (
      <div className="card product-card">
        <a href={link} className="thumb">
          {product.image_url
            ? <img src={product.image_url} alt={product.name} />
            : <span className="icon" aria-hidden="true">{product.icon}</span>}
        </a>
        <a href={link} className="title">{product.name}</a>
        <div className="price">{formatPrice(product.price)}</div>
        <div className={"stock " + stockClass}>{stockText}</div>
        <button className="btn" disabled={product.stock === 0 || busy} onClick={() => onAdd(product)}>
          Add to cart
        </button>
      </div>
    );
  }

  function ProductBrowser() {
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q") || "";

    const [categories, setCategories] = useState([]);
    const [category, setCategory] = useState(params.get("category") || "");
    const [sort, setSort] = useState("");
    const [page, setPage] = useState(1);
    const [data, setData] = useState({ items: [], pages: 1, total: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [toast, setToast] = useState(null);
    const [busyId, setBusyId] = useState(null);

    useEffect(() => {
      api.get("/api/categories").then(setCategories).catch(() => {});
    }, []);

    useEffect(() => {
      let cancelled = false;
      setLoading(true);
      setError(null);

      const query = new URLSearchParams({ page });
      if (q) query.set("q", q);
      if (category) query.set("category_id", category);
      if (sort) query.set("sort", sort);

      api.get("/api/products?" + query.toString())
        .then((result) => { if (!cancelled) setData(result); })
        .catch((e) => { if (!cancelled) setError(e.message); })
        .finally(() => { if (!cancelled) setLoading(false); });

      return () => { cancelled = true; };
    }, [q, category, sort, page]);

    function showToast(text, ok) {
      setToast({ text, ok });
      setTimeout(() => setToast(null), 3000);
    }

    async function addToCart(product) {
      setBusyId(product.id);
      try {
        const cart = await api.post("/api/cart/items", { product_id: product.id, quantity: 1 });
        emitCart(cart);
        showToast(product.name + " was added to your cart", true);
      } catch (e) {
        showToast(e.message, false);
      }
      setBusyId(null);
    }

    function chooseCategory(id) {
      setCategory(id);
      setPage(1);
    }

    return (
      <div className="layout">
        <aside className="sidebar" aria-label="Categories">
          <h2>Categories</h2>
          <button className={"cat" + (category === "" ? " active" : "")} onClick={() => chooseCategory("")}>
            All products
          </button>
          {categories.map((c) => (
            <button key={c.id} className={"cat" + (String(c.id) === String(category) ? " active" : "")}
                    onClick={() => chooseCategory(String(c.id))}>
              <span aria-hidden="true">{c.icon}</span> {c.name}
            </button>
          ))}
        </aside>

        <section>
          <div className="toolbar">
            <p className="muted">
              {loading ? "Loading…" : data.total + (data.total === 1 ? " product" : " products")}
              {q && <span> for “{q}” · <a href="/">Clear search</a></span>}
            </p>
            <label>
              Sort by{" "}
              <select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1); }}>
                <option value="">Featured</option>
                <option value="price_asc">Price: low to high</option>
                <option value="price_desc">Price: high to low</option>
                <option value="name">Name</option>
                <option value="newest">Newest</option>
              </select>
            </label>
          </div>

          {error && <p className="msg err">{error}</p>}

          {!loading && !error && data.items.length === 0 && (
            <div className="empty">
              <p>No products match your search.</p>
              <a className="btn" href="/">Show all products</a>
            </div>
          )}

          <div className="grid">
            {data.items.map((p) => (
              <ProductCard key={p.id} product={p} busy={busyId === p.id} onAdd={addToCart} />
            ))}
          </div>

          {data.pages > 1 && (
            <div className="pager">
              <button className="btn secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
              <span>Page {data.page} of {data.pages}</span>
              <button className="btn secondary" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next</button>
            </div>
          )}
        </section>

        {toast && <div className={"toast " + (toast.ok ? "ok" : "err")} role="status">{toast.text}</div>}
      </div>
    );
  }

  const root = document.getElementById("products-root");
  if (root) ReactDOM.createRoot(root).render(<ProductBrowser />);
})();
