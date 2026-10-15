from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from ..decorators import login_required
from ..extensions import db
from ..models import Order, Product
from ..services import OrderError, change_order_status

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def home():
    return render_template("home.html")


@pages_bp.route("/product/<int:pid>")
def product_detail(pid):
    product = db.get_or_404(Product, pid)
    if not product.is_active and not (g.user and g.user.is_admin):
        abort(404)
    related = (Product.query
               .filter(Product.category_id == product.category_id,
                       Product.id != product.id,
                       Product.is_active.is_(True))
               .limit(4).all())
    return render_template("product.html", product=product, related=related)


@pages_bp.route("/cart")
def cart():
    return render_template("cart.html")


@pages_bp.route("/orders")
@login_required
def orders():
    my_orders = (Order.query.filter_by(user_id=g.user.id)
                 .order_by(Order.created_at.desc()).all())
    return render_template("orders.html", orders=my_orders,
                           placed=request.args.get("placed", type=int))


@pages_bp.route("/orders/<int:oid>/cancel", methods=["POST"])
@login_required
def cancel_order(oid):
    order = db.get_or_404(Order, oid)
    if order.user_id != g.user.id:
        abort(404)  # don't reveal other people's orders
    try:
        change_order_status(order, "cancelled")
        flash(f"Order #{order.id} was cancelled", "success")
    except OrderError as e:
        flash(str(e), "error")
    return redirect(url_for("pages.orders"))
