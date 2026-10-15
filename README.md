# Amazon clone

A small online shop built for learning. Flask + SQLAlchemy on the back end (SQLite locally, or Supabase Postgres), HTML templates for the pages, and React for the interactive parts (product browser, cart, add-to-cart button, cart counter).

## Run it

```bash
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:5000. With no `.env` file the app uses a local SQLite database (`instance/amazon_clone.db`) and adds demo data on first run. To start fresh, stop the server and delete the `instance` folder.

If `pip` is blocked on Windows ("Application Control policy"), use `python -m pip install -r requirements.txt` instead.

The packages are chosen to avoid compiled files, which some Windows security policies block: SQLAlchemy 2.0 runs in plain Python, and `pg8000` is a pure-Python Postgres driver. If you installed an earlier version of this project, remove the old packages first:

```bash
python -m pip uninstall -y psycopg2-binary sqlalchemy
python -m pip install -r requirements.txt
```

## Connect to Supabase

The app talks to Supabase's Postgres database directly (through SQLAlchemy), so it needs your **database connection string**, not the project URL or API keys. Those keys are for Supabase's own REST/JavaScript client, which this app doesn't use. Never put the `service_role` key in front-end code.

1. In Supabase, open your project and click **Connect** at the top. Choose **Session pooler** and copy the URI. (The "Direct connection" string only works on IPv6 networks. The session pooler works on IPv4 and IPv6.)
2. Copy `.env.example` to `.env` (same folder as `run.py`) and fill it in:
   - `DATABASE_URL`: the URI, with `[YOUR-PASSWORD]` replaced by your database password.
   - `SECRET_KEY`: a long random value. Make one with `python -c "import secrets; print(secrets.token_hex(32))"`.
   - `SEED_DEMO_DATA=1` for the first run only (adds 15 demo products and two demo accounts).
3. Run `python run.py`. The tables (`users`, `categories`, `products`, `orders`, `order_items`) are created automatically. You can see them in Supabase under **Table Editor**.
4. Set `SEED_DEMO_DATA=0`, then either delete the two demo users in the Table Editor or change their passwords, because the demo passwords are public. Create your own admin without a demo password with:

```bash
python -m flask --app run create-admin
```

Connection errors: `password authentication failed` means a wrong or badly encoded password; `Network is unreachable` means you used the direct connection instead of the session pooler; `Tenant or user not found` means the username must stay exactly as Supabase gave it (like `postgres.yourprojectref`).

If your password contains special characters such as `@ # / ? %`, URL-encode it before putting it in `DATABASE_URL`:

```bash
python -c "import urllib.parse; print(urllib.parse.quote_plus('your-password'))"
```

Notes:
- **Row Level Security is switched on automatically** for every table. Supabase publishes public tables through its REST API, and without this anyone with your project URL and anon key could read or edit them. The app is not affected, because it connects as the database owner.
- **Product images are still saved on your computer** in `app/static/uploads`, not in Supabase. Supabase Storage is the next step if you want them hosted.
- Local SQLite data is not copied to Supabase. Start with fresh data.

React is loaded from a CDN in the browser, so you need an internet connection when you open the site. There is no build step.

## Demo accounts (local practice only)

| Role | Email | Password |
|---|---|---|
| Admin | admin@example.com | Admin@123 |
| Customer | demo@example.com | Demo@123 |

These exist only when `SEED_DEMO_DATA=1`. Remove or change them, and set a real `SECRET_KEY`, before putting this anywhere public.

## Where things live

```
run.py                 start the server
config.py              settings (reads .env)
.env.example           copy to .env and fill in your Supabase details
app/
  __init__.py          create_app(): wires everything together
  extensions.py        the db object
  models.py            User, Category, Product, Order, OrderItem
  services.py          business logic (checkout, cart, validation, uploads)
  decorators.py        login / admin protection
  errors.py            404 / 500 etc. (HTML pages or JSON for /api)
  seed.py              demo products and users
  dbsetup.py           Supabase hardening (Row Level Security) and the create-admin command
  routes/
    pages.py           home, product, cart, orders
    auth.py            register, login, logout
    admin.py           manage products and orders
    api.py             the JSON API
  templates/           base, home, product, cart, orders, login, register, admin/...
  static/
    css/style.css
    js/api.js          fetch helper
    js/ProductBrowser.jsx, Cart.jsx, AddToCart.jsx, CartBadge.jsx   (React)
    uploads/           product images uploaded by the admin
```

## JSON API

| Method | URL | Who | What |
|---|---|---|---|
| GET | /api/me | anyone | current user or null |
| POST | /api/auth/register, /api/auth/login, /api/auth/logout | anyone | session auth |
| GET | /api/products | anyone | `q`, `category_id`, `min_price`, `max_price`, `sort` (price_asc, price_desc, name, newest), `page`, `per_page` |
| GET | /api/products/<id> | anyone | one product |
| POST | /api/products | admin | create (JSON) |
| PATCH | /api/products/<id> | admin | update some fields |
| DELETE | /api/products/<id> | admin | hides the product (old orders keep working) |
| POST | /api/products/<id>/image | admin | multipart upload, field name `image` |
| GET, POST | /api/categories | anyone / admin | list / create |
| GET | /api/cart | anyone | cart with total |
| POST | /api/cart/items | anyone | `{"product_id": 1, "quantity": 2}` |
| PATCH, DELETE | /api/cart/items/<product_id> | anyone | change quantity / remove |
| POST | /api/checkout | customer | `{"shipping_address": "..."}` creates an order |
| GET | /api/orders, /api/orders/<id> | customer | your orders (admins can open any) |
| POST | /api/orders/<id>/cancel | customer | only while status is `placed`; stock is returned |
| PATCH | /api/orders/<id>/status | admin | placed → shipped → delivered, or placed → cancelled |

Errors are always JSON like `{"error": "message"}` with a proper status code (400, 401, 403, 404, 409, 413).

Try it with curl (the API uses your login cookie):

```bash
curl -c cookies.txt -X POST -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"Admin@123"}' http://127.0.0.1:5000/api/auth/login
curl -b cookies.txt -X POST -H "Content-Type: application/json" \
     -d '{"name":"Garlic","price":40,"stock":25,"category_id":5}' http://127.0.0.1:5000/api/products
```

## What this project does not do yet

- **No payment.** Checkout just creates the order.
- **No CSRF tokens on forms.** The session cookie uses `SameSite=Lax`, which blocks most cross-site attacks, but a production site should add CSRF protection (for example Flask-WTF).
- **Cart is stored in the session**, so it is per browser and lost if cookies are cleared.
- **No migrations.** `create_all()` only creates missing tables. If you change a model, you must change the table yourself (or delete the local SQLite file). Flask-Migrate is the next thing to learn.
- **Stock is not locked**, so two people buying the last item at the same instant could oversell on a busy site.
- **Product images are checked by file extension and size only.**
- **Production:** serve with a real server (for example gunicorn), not `app.run(debug=True)`, and build the React files instead of using Babel in the browser.

## Ideas for next steps

Reviews and ratings, a wishlist, saved addresses, a database-backed cart, password reset, automated tests.
