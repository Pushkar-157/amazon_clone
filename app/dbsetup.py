"""Extra setup that only matters on a hosted Postgres database such as Supabase."""
import click
from sqlalchemy import text

from .extensions import db
from .models import User


def secure_tables():
    """Turn on Row Level Security for every table.

    Supabase automatically publishes tables in the "public" schema through its REST API,
    so anyone holding your project URL and the public (anon) key could read or change them.
    With Row Level Security on and no policies, that API sees nothing. This app is not
    affected because it connects directly to Postgres as the database owner.
    """
    if db.engine.dialect.name != "postgresql":
        return
    unprotected = {
        row[0] for row in db.session.execute(text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = current_schema() AND rowsecurity = false"))
    }
    quote = db.engine.dialect.identifier_preparer.quote
    for table in db.metadata.sorted_tables:
        if table.name in unprotected:
            db.session.execute(text(f"ALTER TABLE {quote(table.name)} ENABLE ROW LEVEL SECURITY"))
    db.session.commit()


def register_cli(app):
    @app.cli.command("create-admin")
    def create_admin():
        """Create an admin account, or promote an existing user, without demo passwords."""
        email = click.prompt("Admin email").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_admin = True
            db.session.commit()
            click.echo(f"{email} is now an admin.")
            return
        name = click.prompt("Name").strip()
        password = click.prompt("Password (at least 6 characters)", hide_input=True,
                                confirmation_prompt=True)
        from .services import create_user
        try:
            user = create_user(name, email, password)
        except ValueError as e:
            raise click.ClickException(str(e))
        user.is_admin = True
        db.session.commit()
        click.echo(f"Admin account created for {email}.")
