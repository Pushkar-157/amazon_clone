import os
import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

# Reads the .env file in this folder (if there is one) into environment variables.
load_dotenv()


def database_settings():
    """Return (database url, extra connection arguments).

    Uses DATABASE_URL from .env (your Supabase connection string).
    If it is empty, a local SQLite file is used instead.
    """
    raw = os.environ.get("DATABASE_URL", "").strip()
    if not raw:
        return "sqlite:///amazon_clone.db", {}

    parts = urlsplit(raw)
    if not parts.scheme.startswith("postgres"):
        return raw, {}

    # Supabase shows "postgresql://..." or "postgres://...". Tell SQLAlchemy to use pg8000,
    # a Postgres driver written in pure Python (no compiled files, so Windows
    # Application Control policies cannot block it).
    query = parse_qsl(parts.query)
    sslmode = dict(query).get("sslmode")
    query = [(k, v) for k, v in query if k != "sslmode"]  # pg8000 does not accept this option
    url = urlunsplit(("postgresql+pg8000", parts.netloc, parts.path, urlencode(query), parts.fragment))

    # Supabase only accepts encrypted connections. Encrypt everything except local databases.
    is_local = parts.hostname in (None, "localhost", "127.0.0.1", "::1")
    if is_local or sslmode == "disable":
        return url, {}
    context = ssl.create_default_context()
    context.check_hostname = False       # same behaviour as sslmode=require:
    context.verify_mode = ssl.CERT_NONE  # encrypted, but the server certificate is not verified
    return url, {"ssl_context": context}


DATABASE_URL, CONNECT_ARGS = database_settings()
USING_POSTGRES = DATABASE_URL.startswith("postgresql")


class Config:
    SITE_NAME = "Amazon clone"
    # In production, set SECRET_KEY in .env or as an environment variable.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Keep a few connections open, and replace ones the server has closed.
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"pool_pre_ping": True, "pool_recycle": 280, "pool_size": 5, "max_overflow": 5,
         "connect_args": CONNECT_ARGS}
        if USING_POSTGRES else {}
    )

    # Demo products and demo accounts with PUBLIC passwords.
    # On by default for local SQLite, off by default for a real Postgres/Supabase database.
    SEED_DEMO_DATA = os.environ.get("SEED_DEMO_DATA", "0" if USING_POSTGRES else "1") == "1"

    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # reject uploads over 2 MB
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PER_PAGE = 8
