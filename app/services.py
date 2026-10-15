"""Business logic shared by the HTML pages and the JSON API."""
import os
import uuid

from flask import current_app, session

from .extensions import db
from .models import STATUS_FLOW, Category, Order, OrderItem, Product, User

ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "webp"}


class CheckoutError(Exception):
    pass


class OrderError(Exception):
    pass


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# ---------- users ----------

def create_user(name, email, password):
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""
    if not name or len(name) > 80:
        raise ValueError("Please enter your name")
    if "@" not in email or len(email) > 120:
        raise ValueError("Please enter a valid email address")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    if User.query.filter_by(email=email).first():
        raise ValueError("That email is already registered")

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(email, password):
    user = User.query.filter_by(email=(email or "").strip().lower()).first()
    if user and user.check_password(password or ""):
        return user
    return None


def start_session(user):
    """Log a user in. A guest's cart is kept."""
    cart = session.get("cart")
    session.clear()
    if cart:
        session["cart"] = cart
    session["user_id"] = user.id


# ---------- products ----------

def validate_product(data, partial=False):
    """Return a dict of field errors. An empty dict means the data is valid."""
    errors = {}

    if not partial or "name" in data:
        name = data.get("name")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
            errors["name"] = "Name is required (max 120 characters)"

    if not partial or "price" in data:
        price = data.get("price")
        if not is_number(price) or price <= 0 or price > 10_000_000:
            errors["price"] = "Price must be a positive number"

    if "stock" in data:
        stock = data["stock"]
        if not is_int(stock) or stock < 0:
            errors["stock"] = "Stock must be a whole number, 0 or more"

    if "description" in data and data["description"] is not None:
        if not isinstance(data["description"], str):
            errors["description"] = "Description must be text"

    if "category_id" in data and data["category_id"] is not None:
        cid = data["category_id"]
        if not is_int(cid) or db.session.get(Category, cid) is None:
            errors["category_id"] = "Category does not exist"

    if "is_active" in data and not isinstance(data["is_active"], bool):
        errors["is_active"] = "is_active must be true or false"

    return errors


def apply_product_data(product, data):
    if "name" in data:
        product.name = data["name"].strip()
    if "price" in data:
        product.price = float(data["price"])
    if "stock" in data:
        product.stock = data["stock"]
    if "description" in data:
        product.description = (data["description"] or "").strip()
    if "category_id" in data:
        product.category_id = data["category_id"]
    if "is_active" in data:
        product.is_active = data["is_active"]


def save_image(file):
    """Validate and store an uploaded image. Returns the new filename, or None if no file."""
    if file is None or file.filename == "":
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_IMAGE_TYPES:
        raise ValueError("Only png, jpg, jpeg and webp images are allowed")
    filename = f"{uuid.uuid4().hex}.{ext}"  # never trust the user's filename
    file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
    return filename


def delete_image(filename):
    if filename:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(filename))
        if os.path.exists(path):
            os.remove(path)


# ---------- cart ----------
# The cart lives in the session as {"<product_id>": quantity}.

def cart_lines(cart):
    lines = []
    for pid, qty in cart.items():
        product = db.session.get(Product, int(pid))
        if product and product.is_active:
            lines.append((product, qty))
    return lines


def cart_summary(cart):
    lines = cart_lines(cart)
    items = [
        {"product": p.to_dict(), "quantity": q, "subtotal": round(p.price * q, 2)}
        for p, q in lines
    ]
    return {
        "items": items,
        "total": round(sum(i["subtotal"] for i in items), 2),
        "count": sum(q for _, q in lines),
    }


# ---------- orders ----------

def place_order(user, cart, address):
    address = (address or "").strip()
    if len(address) < 10 or len(address) > 255:
        raise CheckoutError("Please enter your full shipping address (10 to 255 characters)")
    if not cart:
        raise CheckoutError("Your cart is empty")

    lines = cart_lines(cart)
    if not lines or len(lines) != len(cart):
        raise CheckoutError("Some items in your cart are no longer available")

    try:
        order = Order(user_id=user.id, shipping_address=address)
        for product, qty in lines:
            if product.stock < qty:
                raise CheckoutError(f"Not enough stock for {product.name} (only {product.stock} left)")
            product.stock -= qty
            order.items.append(OrderItem(product_id=product.id, quantity=qty, price=product.price))
        db.session.add(order)
        db.session.commit()
        return order
    except CheckoutError:
        db.session.rollback()
        raise


def change_order_status(order, new_status):
    if new_status not in STATUS_FLOW:
        raise OrderError("Unknown status")
    if new_status not in STATUS_FLOW[order.status]:
        raise OrderError(f"An order that is {order.status} cannot become {new_status}")
    if new_status == "cancelled":
        for item in order.items:  # put the stock back
            item.product.stock += item.quantity
    order.status = new_status
    db.session.commit()
    return order
