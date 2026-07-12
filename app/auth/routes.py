from flask import Blueprint, redirect, render_template, url_for
from flask_login import login_user, logout_user, login_required

from app.extensions import db, login_manager, oauth
from app.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    """Tells Flask-Login how to turn the id stored in the session
    cookie back into a real User object on each request."""
    return db.session.get(User, int(user_id))


@auth_bp.route("/login")
def login():
    return render_template("auth/login.html")


@auth_bp.route("/login/google")
def login_google():
    """Step 1 of the OAuth handshake: send the browser to Google's
    consent screen, telling Google where to send it back afterward."""
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/login/google/callback")
def google_callback():
    """Step 2: Google redirects back here with a code. Authlib
    exchanges it for a token and the user's verified profile info."""
    token = oauth.google.authorize_access_token()
    user_info = token["userinfo"]

    user = User.query.filter_by(google_id=user_info["sub"]).first()
    if user is None:
        user = User(
            google_id=user_info["sub"],
            email=user_info["email"],
            name=user_info.get("name", user_info["email"]),
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for("contacts.index"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
