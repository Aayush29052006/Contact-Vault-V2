import os

from flask import Flask
from dotenv import load_dotenv

# Must run before Config is imported below - Config reads os.environ.get(...)
# at class-definition time, so .env has to be loaded into the environment
# first, or every value from .env (DATABASE_URL, etc.) is silently ignored
# in favor of whatever was already in the environment (or the fallback).
load_dotenv()

from app.config import Config
from app.extensions import db, migrate, login_manager, oauth, csrf


def create_app(config_class=Config):
    """Application factory: builds and wires up a Flask app instance.

    Using a factory (instead of a module-level `app = Flask(__name__)`)
    is what lets tests spin up a fresh app with TestConfig, separate
    from whatever config real usage runs under.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # instance/ is gitignored (it holds the local SQLite file), so a
    # fresh clone never has this folder on disk. Without this, SQLite
    # fails with "unable to open database file" - it can create the
    # .db file itself, but not the parent directory.
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    oauth.init_app(app)
    csrf.init_app(app)

    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    # Models must be imported somewhere before Alembic's autogenerate
    # runs, or it won't see them and will produce an empty migration.
    from app import models  # noqa: F401

    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    from app.contacts.routes import contacts_bp
    app.register_blueprint(contacts_bp)

    from app.utils import time_ago
    app.jinja_env.filters["timeago"] = time_ago

    return app
