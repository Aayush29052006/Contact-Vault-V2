from flask import Flask
from dotenv import load_dotenv

from app.config import Config
from app.extensions import db, migrate, login_manager, oauth

load_dotenv()


def create_app(config_class=Config):
    """Application factory: builds and wires up a Flask app instance.

    Using a factory (instead of a module-level `app = Flask(__name__)`)
    is what lets tests spin up a fresh app with TestConfig, separate
    from whatever config real usage runs under.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    oauth.init_app(app)

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

    # from app.contacts.routes import contacts_bp
    # app.register_blueprint(contacts_bp)

    return app
