import os

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    """Base config, loaded from environment variables (see .env.example)."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(basedir, 'instance', 'contactvault.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")


class TestConfig(Config):
    """Used by the test suite: in-memory DB, no CSRF friction, no real secrets needed."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
