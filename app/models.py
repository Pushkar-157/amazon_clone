from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

ORDER_STATUSES = ("placed", "shipped", "delivered", "cancelled")
# Which status an order may move to from its current one.
STATUS_FLOW = {
    "placed": {"shipped", "cancelled"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    orders = db.relationship("Order", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "is_admin": self.is_admin}


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    icon = db.Column(db.String(8), default="🛍️")

    products = db.relationship("Product", backref="category", lazy=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "icon": self.icon}


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    image = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # hide instead of delete
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    @property
    def image_url(self):
        return f"/static/uploads/{self.image}" if self.image else None

    @property
    def icon(self):
        return self.category.icon if self.category else "🛍️"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description or "",
            "price": self.price,
            "stock": self.stock,
            "image_url": self.image_url,
            "icon": self.icon,
            "category_id": self.category_id,
            "category": self.category.name if self.category else None,
            "is_active": self.is_active,
        }


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="placed", nullable=False)
    shipping_address = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")

    @property
    def total(self):
        return round(sum(i.price * i.quantity for i in self.items), 2)

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "shipping_address": self.shipping_address,
            "created_at": self.created_at.isoformat(),
            "total": self.total,
            "items": [i.to_dict() for i in self.items],
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # price at the time of purchase

    product = db.relationship("Product")

    def to_dict(self):
        return {
            "product_id": self.product_id,
            "name": self.product.name,
            "quantity": self.quantity,
            "price": self.price,
            "subtotal": round(self.price * self.quantity, 2),
        }
