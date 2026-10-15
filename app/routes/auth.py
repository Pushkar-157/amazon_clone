from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from ..services import authenticate, create_user, start_session

auth_bp = Blueprint("auth", __name__)


def safe_next(target):
    """Only allow redirects to paths on this site."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for("pages.home")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("pages.home"))
    if request.method == "POST":
        try:
            user = create_user(request.form.get("name"), request.form.get("email"),
                               request.form.get("password"))
        except ValueError as e:
            flash(str(e), "error")
            return render_template("register.html")
        start_session(user)
        flash(f"Welcome, {user.name}! Your account is ready.", "success")
        return redirect(url_for("pages.home"))
    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("pages.home"))
    if request.method == "POST":
        user = authenticate(request.form.get("email"), request.form.get("password"))
        if user:
            start_session(user)
            flash(f"Welcome back, {user.name}", "success")
            return redirect(safe_next(request.form.get("next")))
        # Same message for a wrong email or a wrong password.
        flash("Email or password is incorrect", "error")
    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out", "success")
    return redirect(url_for("pages.home"))
