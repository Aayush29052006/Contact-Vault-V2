from datetime import datetime, timezone

from flask_login import UserMixin

from app.extensions import db


class User(UserMixin, db.Model):
    """A person who has signed in with their Google account.

    UserMixin supplies the properties/methods Flask-Login needs
    (is_authenticated, is_active, get_id, ...) - get_id() works
    automatically off our `id` column, no override needed.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    contacts = db.relationship(
        "Contact", back_populates="owner", cascade="all, delete-orphan", lazy="dynamic"
    )
    activity_logs = db.relationship(
        "ActivityLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="ActivityLog.created_at.desc()",
    )

    def __repr__(self):
        return f"<User {self.email}>"
