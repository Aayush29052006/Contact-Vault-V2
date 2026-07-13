from datetime import datetime, timezone

from app.extensions import db


class ActivityLog(db.Model):
    """A permanent, timestamped record of what a user did - unlike the
    flash messages in the UI, which disappear after one page load."""

    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    undo_data = db.Column(db.Text, nullable=True)

    user = db.relationship("User", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog {self.description!r}>"
