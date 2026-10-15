from .extensions import db
from .models import Category, Product, User

CATEGORIES = [
    ("Electronics", "🎧"),
    ("Books", "📚"),
    ("Home & Kitchen", "🍳"),
    ("Fashion", "👕"),
    ("Grocery", "🛒"),
]

PRODUCTS = [
    ("Wireless Earbuds", 1999, 25, "Electronics", "Bluetooth 5.3 earbuds with a charging case and up to 24 hours of playback."),
    ("Bluetooth Speaker", 2499, 15, "Electronics", "Waterproof portable speaker with deep bass and 12 hours of battery."),
    ("USB-C Fast Charger", 799, 60, "Electronics", "30W wall charger that fills most phones to 50% in about 30 minutes."),
    ("Smart Watch", 3999, 4, "Electronics", "Heart-rate, sleep and step tracking with a bright 1.8 inch display."),
    ("Learn Python the Easy Way", 499, 40, "Books", "A beginner-friendly guide with small projects in every chapter."),
    ("Mystery at Midnight", 299, 30, "Books", "A fast-paced detective novel set over one stormy night."),
    ("The Habit Handbook", 349, 0, "Books", "Practical routines for building habits that last."),
    ("Non-stick Frying Pan", 899, 22, "Home & Kitchen", "26 cm pan with an even-heating base and a cool-touch handle."),
    ("Steel Water Bottle", 449, 80, "Home & Kitchen", "1 litre insulated bottle that keeps drinks cold for 24 hours."),
    ("Ceramic Mug Set (4)", 599, 18, "Home & Kitchen", "Four 300 ml mugs, microwave and dishwasher safe."),
    ("Cotton T-Shirt", 399, 100, "Fashion", "Soft 100% cotton crew-neck tee in a regular fit."),
    ("Running Shoes", 2199, 12, "Fashion", "Lightweight cushioned shoes for daily runs."),
    ("Canvas Backpack", 1299, 20, "Fashion", "20 litre backpack with a padded laptop sleeve."),
    ("Basmati Rice 5 kg", 650, 45, "Grocery", "Long-grain aged basmati with a fragrant aroma."),
    ("Masala Chai Blend", 250, 3, "Grocery", "Strong Assam tea blended with cardamom, ginger and cloves."),
]


def seed():
    """Add demo data on first run only. Change these passwords before deploying anywhere real."""
    if Category.query.count() == 0:
        cats = {name: Category(name=name, icon=icon) for name, icon in CATEGORIES}
        db.session.add_all(cats.values())
        db.session.flush()
        for name, price, stock, cat, description in PRODUCTS:
            db.session.add(Product(name=name, price=price, stock=stock,
                                   description=description, category=cats[cat]))
        db.session.commit()

    if User.query.count() == 0:
        admin = User(name="Admin", email="admin@example.com", is_admin=True)
        admin.set_password("Admin@123")
        demo = User(name="Demo Customer", email="demo@example.com")
        demo.set_password("Demo@123")
        db.session.add_all([admin, demo])
        db.session.commit()
