import os

# Run SQLAlchemy in plain Python. Its optional compiled add-ons are not needed here,
# and some Windows security policies (Application Control) block them.
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT_RUNTIME", "1")

from flask import Flask, g, session

from .extensions import db


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    os.makedirs(app.instance_path, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = os.path.join(app.static_folder, "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    from .models import User

    @app.before_request
    def load_user():
        user_id = session.get("user_id")
        g.user = db.session.get(User, user_id) if user_id else None

    from .routes.pages import pages_bp
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.api import api_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    from .errors import register_error_handlers
    register_error_handlers(app)

    from .dbsetup import register_cli, secure_tables
    register_cli(app)

    with app.app_context():
        db.create_all()
        secure_tables()
        if app.config["SEED_DEMO_DATA"]:
            from .seed import seed
            seed()

    return app
