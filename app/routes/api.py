from flask import Blueprint, current_app, g, jsonify, request, session

from ..decorators import api_admin_required, api_login_required
from ..extensions import db
from ..models import Category, Order, Product
from ..services import (CheckoutError, OrderError, apply_product_data, authenticate,
                        cart_summary, change_order_status, create_user, delete_image,
                        is_int, place_order, save_image, start_session, validate_product)

api_bp = Blueprint("api", __name__)

SORTS = {
    "price_asc": Product.price.asc(),
    "price_desc": Product.price.desc(),
    "name": Product.name.asc(),
    "newest": Product.id.desc(),
}


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def bad_json():
    return jsonify({"error": "Request body must be a JSON object"}), 400


# ---------- auth ----------

@api_bp.route("/me")
def me():
    return jsonify({"user": g.user.to_dict() if g.user else None})


@api_bp.route("/auth/register", methods=["POST"])
def register():
    data = json_body()
    if data is None:
        return bad_json()
    try:
        user = create_user(data.get("name"), data.get("email"), data.get("password"))
    except (ValueError, TypeError, AttributeError) as e:
        return jsonify({"error": str(e) if isinstance(e, ValueError) else "Invalid data"}), 400
    start_session(user)
    return jsonify(user.to_dict()), 201


@api_bp.route("/auth/login", methods=["POST"])
def login():
    data = json_body()
    if data is None:
        return bad_json()
    email, password = data.get("email"), data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "Email and password are required"}), 400
    user = authenticate(email, password)
    if user is None:
        return jsonify({"error": "Email or password is incorrect"}), 401
    start_session(user)
    return jsonify(user.to_dict())


@api_bp.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return "", 204


# ---------- categories ----------

@api_bp.route("/categories")
def list_categories():
    return jsonify([c.to_dict() for c in Category.query.order_by(Category.name)])


@api_bp.route("/categories", methods=["POST"])
@api_admin_required
def create_category():
    data = json_body()
    if data is None:
        return bad_json()
    name = data.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 50:
        return jsonify({"error": "Name is required (max 50 characters)"}), 400
    if Category.query.filter_by(name=name.strip()).first():
        return jsonify({"error": "Category already exists"}), 409
    icon = data.get("icon") if isinstance(data.get("icon"), str) else "🛍️"
    category = Category(name=name.strip(), icon=icon[:8])
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


# ---------- products ----------

@api_bp.route("/products")
def list_products():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", current_app.config["PER_PAGE"], type=int), 1), 50)
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)

    query = Product.query.filter(Product.is_active.is_(True))
    if q:
        like = f"%{q}%"
        query = query.filter(Product.name.ilike(like) | Product.description.ilike(like))
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    order = SORTS.get(request.args.get("sort", ""), Product.id.asc())
    pagination = query.order_by(order).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [p.to_dict() for p in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages or 1,
        "total": pagination.total,
    })


@api_bp.route("/products/<int:pid>")
def get_product(pid):
    product = db.get_or_404(Product, pid)
    if not product.is_active and not (g.user and g.user.is_admin):
        return jsonify({"error": "We couldn't find that page"}), 404
    return jsonify(product.to_dict())


@api_bp.route("/products", methods=["POST"])
@api_admin_required
def create_product():
    data = json_body()
    if data is None:
        return bad_json()
    errors = validate_product(data)
    if errors:
        return jsonify({"error": "Validation failed", "fields": errors}), 400
    product = Product(stock=0)
    apply_product_data(product, data)
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict()), 201


@api_bp.route("/products/<int:pid>", methods=["PATCH"])
@api_admin_required
def update_product(pid):
    product = db.get_or_404(Product, pid)
    data = json_body()
    if data is None:
        return bad_json()
    errors = validate_product(data, partial=True)
    if errors:
        return jsonify({"error": "Validation failed", "fields": errors}), 400
    apply_product_data(product, data)
    db.session.commit()
    return jsonify(product.to_dict())


@api_bp.route("/products/<int:pid>", methods=["DELETE"])
@api_admin_required
def delete_product(pid):
    """Products are hidden, not deleted, so old orders keep working."""
    product = db.get_or_404(Product, pid)
    product.is_active = False
    db.session.commit()
    return "", 204


@api_bp.route("/products/<int:pid>/image", methods=["POST"])
@api_admin_required
def upload_product_image(pid):
    product = db.get_or_404(Product, pid)
    try:
        filename = save_image(request.files.get("image"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if filename is None:
        return jsonify({"error": "No image file provided (form field name: image)"}), 400
    delete_image(product.image)
    product.image = filename
    db.session.commit()
    return jsonify(product.to_dict())


# ---------- cart (kept in the session) ----------

@api_bp.route("/cart")
def get_cart():
    return jsonify(cart_summary(session.get("cart", {})))


@api_bp.route("/cart/items", methods=["POST"])
def add_cart_item():
    data = json_body()
    if data is None:
        return bad_json()
    pid, qty = data.get("product_id"), data.get("quantity", 1)
    if not is_int(pid) or not is_int(qty) or qty < 1:
        return jsonify({"error": "product_id and quantity must be positive whole numbers"}), 400
    product = db.session.get(Product, pid)
    if product is None or not product.is_active:
        return jsonify({"error": "Product not found"}), 404

    cart = session.get("cart", {})
    new_qty = cart.get(str(pid), 0) + qty
    if new_qty > product.stock:
        return jsonify({"error": f"Only {product.stock} in stock"}), 409
    cart[str(pid)] = new_qty
    session["cart"] = cart
    return jsonify(cart_summary(cart)), 201


@api_bp.route("/cart/items/<int:pid>", methods=["PATCH"])
def update_cart_item(pid):
    cart = session.get("cart", {})
    if str(pid) not in cart:
        return jsonify({"error": "That item is not in your cart"}), 404
    data = json_body()
    qty = data.get("quantity") if data else None
    if not is_int(qty) or qty < 1:
        return jsonify({"error": "quantity must be a positive whole number"}), 400
    product = db.session.get(Product, pid)
    if product is None or not product.is_active:
        return jsonify({"error": "This product is no longer available"}), 404
    if qty > product.stock:
        return jsonify({"error": f"Only {product.stock} in stock"}), 409
    cart[str(pid)] = qty
    session["cart"] = cart
    return jsonify(cart_summary(cart))


@api_bp.route("/cart/items/<int:pid>", methods=["DELETE"])
def remove_cart_item(pid):
    cart = session.get("cart", {})
    if cart.pop(str(pid), None) is None:
        return jsonify({"error": "That item is not in your cart"}), 404
    session["cart"] = cart
    return jsonify(cart_summary(cart))


# ---------- checkout and orders ----------

@api_bp.route("/checkout", methods=["POST"])
@api_login_required
def checkout():
    data = json_body()
    if data is None:
        return bad_json()
    address = data.get("shipping_address")
    if not isinstance(address, str):
        return jsonify({"error": "shipping_address is required"}), 400
    try:
        order = place_order(g.user, session.get("cart", {}), address)
    except CheckoutError as e:
        return jsonify({"error": str(e)}), 400
    session.pop("cart", None)
    return jsonify(order.to_dict()), 201


@api_bp.route("/orders")
@api_login_required
def list_orders():
    orders = (Order.query.filter_by(user_id=g.user.id)
              .order_by(Order.created_at.desc()).all())
    return jsonify([o.to_dict() for o in orders])


def get_visible_order(oid):
    """Customers can only see their own orders. Admins can see all."""
    order = db.session.get(Order, oid)
    if order is None or (order.user_id != g.user.id and not g.user.is_admin):
        return None
    return order


@api_bp.route("/orders/<int:oid>")
@api_login_required
def get_order(oid):
    order = get_visible_order(oid)
    if order is None:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order.to_dict())


@api_bp.route("/orders/<int:oid>/cancel", methods=["POST"])
@api_login_required
def cancel_order(oid):
    order = get_visible_order(oid)
    if order is None or order.user_id != g.user.id:
        return jsonify({"error": "Order not found"}), 404
    try:
        change_order_status(order, "cancelled")
    except OrderError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(order.to_dict())


@api_bp.route("/orders/<int:oid>/status", methods=["PATCH"])
@api_admin_required
def update_order_status(oid):
    order = db.get_or_404(Order, oid)
    data = json_body()
    status = data.get("status") if data else None
    if not isinstance(status, str):
        return jsonify({"error": "status is required"}), 400
    try:
        change_order_status(order, status)
    except OrderError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(order.to_dict())
