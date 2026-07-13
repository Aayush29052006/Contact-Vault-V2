from unittest.mock import patch

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db


class CSRFEnabledConfig(TestConfig):
    WTF_CSRF_ENABLED = True


def test_state_changing_post_without_csrf_token_is_rejected():
    """Proves CSRFProtect is actually wired in app-wide, not just on
    forms that happen to use FlaskForm. Uses its own app instance since
    every other test intentionally runs with CSRF disabled for
    convenience."""
    app = create_app(CSRFEnabledConfig)
    with app.app_context():
        _db.create_all()
        client = app.test_client()

        fake_userinfo = {"sub": "google-1", "email": "user@example.com", "name": "Test User"}
        with patch("app.auth.routes.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token.return_value = {"userinfo": fake_userinfo}
            client.get("/auth/login/google/callback")

        # No csrf_token at all - this is exactly what a forged
        # cross-site request would look like.
        response = client.post("/undo")
        assert response.status_code == 400

        _db.drop_all()
