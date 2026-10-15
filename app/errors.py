from flask import jsonify, render_template, request

from .extensions import db


def wants_json():
    return request.path.startswith("/api/")


def register_error_handlers(app):
    def respond(message, status, template="404.html"):
        if wants_json():
            return jsonify({"error": message}), status
        return render_template(template, message=message, status=status), status

    @app.errorhandler(400)
    def bad_request(e):
        return respond("Bad request", 400)

    @app.errorhandler(404)
    def not_found(e):
        return respond("We couldn't find that page", 404)

    @app.errorhandler(405)
    def method_not_allowed(e):
        return respond("Method not allowed", 405)

    @app.errorhandler(413)
    def too_large(e):
        return respond("File too large (max 2 MB)", 413)

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return respond("Something went wrong on our side", 500, "500.html")
