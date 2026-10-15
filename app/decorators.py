from functools import wraps

from flask import flash, g, jsonify, redirect, request, url_for


def login_required(view):
    """For HTML pages: send guests to the login page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please sign in to continue", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def api_login_required(view):
    """For the JSON API: return 401 instead of redirecting."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return jsonify({"error": "Authentication required"}), 401
        return view(*args, **kwargs)
    return wrapped


def api_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return jsonify({"error": "Authentication required"}), 401
        if not g.user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
        return view(*args, **kwargs)
    return wrapped
