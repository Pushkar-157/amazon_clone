from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ..extensions import db
from ..models import ORDER_STATUSES, Category, Order, Product
from ..services import (OrderError, apply_product_data, change_order_status,
                        delete_image, save_image, validate_product)

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
def require_admin():
    if g.user is None or not g.user.is_admin:
        flash("That page is for admins only", "error")
        return redirect(url_for("pages.home"))


def read_product_form():
    f = request.form
    data = {"name": f.get("name", "").strip(), "description": f.get("description", "").strip()}
    try:
        data["price"] = float(f.get("price", ""))
    except ValueError:
        data["price"] = None
    try:
        data["stock"] = int(f.get("stock", "0"))
    except ValueError:
        data["stock"] = -1
    category = f.get("category_id", "")
    data["category_id"] = int(category) if category.isdigit() else None
    return data


@admin_bp.route("/")
def dashboard():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin/products.html", products=products)


@admin_bp.route("/products/new", methods=["GET", "POST"])
def new_product():
    categories = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        data = read_product_form()
        errors = validate_product(data)
        if errors:
            flash(" ".join(errors.values()), "error")
            return render_template("admin/product_form.html", product=data, categories=categories, is_new=True)
        try:
            filename = save_image(request.files.get("image"))
        except ValueError as e:
            flash(str(e), "error")
            return render_template("admin/product_form.html", product=data, categories=categories, is_new=True)
        product = Product(image=filename)
        apply_product_data(product, data)
        db.session.add(product)
        db.session.commit()
        flash(f"{product.name} was added", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/product_form.html", product={"stock": 0}, categories=categories, is_new=True)


@admin_bp.route("/products/<int:pid>/edit", methods=["GET", "POST"])
def edit_product(pid):
    product = db.get_or_404(Product, pid)
    categories = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        data = read_product_form()
        errors = validate_product(data)
        if errors:
            flash(" ".join(errors.values()), "error")
            return render_template("admin/product_form.html", product=data, categories=categories, is_new=False, pid=pid)
        try:
            filename = save_image(request.files.get("image"))
        except ValueError as e:
            flash(str(e), "error")
            return render_template("admin/product_form.html", product=data, categories=categories, is_new=False, pid=pid)
        if filename:
            delete_image(product.image)
            product.image = filename
        apply_product_data(product, data)
        db.session.commit()
        flash(f"{product.name} was updated", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/product_form.html", product=product, categories=categories, is_new=False, pid=pid)


@admin_bp.route("/products/<int:pid>/toggle", methods=["POST"])
def toggle_product(pid):
    product = db.get_or_404(Product, pid)
    product.is_active = not product.is_active
    db.session.commit()
    flash(f"{product.name} is now {'visible' if product.is_active else 'hidden'}", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/orders")
def orders():
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=all_orders, statuses=ORDER_STATUSES)


@admin_bp.route("/orders/<int:oid>/status", methods=["POST"])
def update_order_status(oid):
    order = db.get_or_404(Order, oid)
    try:
        change_order_status(order, request.form.get("status", ""))
        flash(f"Order #{order.id} is now {order.status}", "success")
    except OrderError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.orders"))
