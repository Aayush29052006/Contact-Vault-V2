import os
from pathlib import Path

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# .as_posix() forces forward slashes regardless of OS - required because
# SQLite connection URLs are a URI format, not a native file path. On
# Windows, os.path.join() gives backslashes, which SQLite's URL parser
# cannot open ("unable to open database file") even though the path
# looks correct to a human.
_default_db_path = (Path(basedir) / "instance" / "contactvault.db").as_posix()


class Config:
    """Base config, loaded from environment variables (see .env.example)."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{_default_db_path}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")


class TestConfig(Config):
    """Used by the test suite: in-memory DB, no CSRF friction, no real secrets needed."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
