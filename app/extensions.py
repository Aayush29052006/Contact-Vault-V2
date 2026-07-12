from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Single shared instances, initialized against a real Flask app
# inside create_app() (app/__init__.py). This split avoids circular
# imports: models import `db` from here, not from app/__init__.py.
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
