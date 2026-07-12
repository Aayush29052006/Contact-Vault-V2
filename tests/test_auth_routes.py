from unittest.mock import patch

from flask import redirect

from app.models.user import User


class TestAuthRoutes:
    def test_login_page_loads(self, client):
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert b"Continue with Google" in response.data

    def test_login_google_redirects_to_google(self, client):
        with patch("app.auth.routes.oauth") as mock_oauth:
            mock_oauth.google.authorize_redirect.return_value = redirect(
                "https://accounts.google.com/mock-consent-screen"
            )
            response = client.get("/auth/login/google")

        assert response.status_code == 302
        assert "accounts.google.com" in response.location

    def test_callback_creates_new_user_on_first_login(self, client, session):
        fake_userinfo = {"sub": "google-999", "email": "new@example.com", "name": "New Person"}

        with patch("app.auth.routes.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token.return_value = {"userinfo": fake_userinfo}
            response = client.get("/auth/login/google/callback")

        assert response.status_code == 302
        assert response.location == "/"
        user = User.query.filter_by(google_id="google-999").first()
        assert user is not None
        assert user.email == "new@example.com"

    def test_callback_logs_in_existing_user_without_duplicating(self, client, session):
        existing = User(google_id="google-1", email="existing@example.com", name="Existing Person")
        session.add(existing)
        session.commit()

        fake_userinfo = {"sub": "google-1", "email": "existing@example.com", "name": "Existing Person"}
        with patch("app.auth.routes.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token.return_value = {"userinfo": fake_userinfo}
            client.get("/auth/login/google/callback")

        assert User.query.filter_by(google_id="google-1").count() == 1

    def test_logout_requires_login_first(self, client):
        response = client.get("/auth/logout")
        # Flask-Login redirects anonymous users to the configured login_view
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_logged_in_user_can_logout(self, client, session):
        fake_userinfo = {"sub": "google-42", "email": "logout@example.com", "name": "Log Out"}
        with patch("app.auth.routes.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token.return_value = {"userinfo": fake_userinfo}
            client.get("/auth/login/google/callback")

        response = client.get("/auth/logout")
        assert response.status_code == 302
        assert "/auth/login" in response.location
