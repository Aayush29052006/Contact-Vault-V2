from datetime import datetime, timezone

from sqlalchemy import func

from app.extensions import db


class Contact(db.Model):
    """A single contact, owned by exactly one User.

    Case-insensitive duplicate prevention happens at two levels:
      1. In ContactService (next step) - checked before insert, so we
         can show a friendly "already exists" message.
      2. Here, via a functional unique index on (user_id, lower(email)) -
         a safety net so a duplicate can never land in the database even
         if the service-layer check is ever bypassed or has a bug.
    """

    __tablename__ = "contacts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    owner = db.relationship("User", back_populates="contacts")

    __table_args__ = (
        db.Index("uq_contacts_user_email_ci", "user_id", func.lower(email), unique=True),
    )

    def __repr__(self):
        return f"<Contact {self.name} <{self.email}>>"
