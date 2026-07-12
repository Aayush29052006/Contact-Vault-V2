import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db


@pytest.fixture
def app():
    """A fresh Flask app, configured for testing, with tables created
    in an in-memory SQLite database that's thrown away after the test."""
    app = create_app(TestConfig)

    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def session(db):
    return db.session


@pytest.fixture
def client(app):
    return app.test_client()


def login_via_google(client, google_id="google-1", email="user@example.com", name="Test User"):
    """Logs a client in by mocking the OAuth callback, the same way
    test_auth_routes.py does - reused here so other test files don't
    need real Google credentials or a browser to test logged-in routes."""
    from unittest.mock import patch

    fake_userinfo = {"sub": google_id, "email": email, "name": name}
    with patch("app.auth.routes.oauth") as mock_oauth:
        mock_oauth.google.authorize_access_token.return_value = {"userinfo": fake_userinfo}
        client.get("/auth/login/google/callback")


@pytest.fixture
def logged_in_client(client):
    """A test client that's already logged in as one user, plus that
    user object for making assertions."""
    from app.models.user import User

    login_via_google(client)
    user = User.query.filter_by(google_id="google-1").first()
    return client, user
