import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User


def make_user(**overrides):
    defaults = {"google_id": "google-123", "email": "aayush@example.com", "name": "Aayush"}
    defaults.update(overrides)
    return User(**defaults)


class TestUserModel:
    def test_create_user(self, session):
        user = make_user()
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.email == "aayush@example.com"
        assert user.created_at is not None

    def test_repr(self, session):
        user = make_user()
        session.add(user)
        session.commit()

        assert repr(user) == "<User aayush@example.com>"

    def test_google_id_must_be_unique(self, session):
        session.add(make_user(google_id="dup-id", email="a@example.com"))
        session.commit()

        session.add(make_user(google_id="dup-id", email="b@example.com"))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_email_must_be_unique(self, session):
        session.add(make_user(google_id="id-1", email="dup@example.com"))
        session.commit()

        session.add(make_user(google_id="id-2", email="dup@example.com"))
        with pytest.raises(IntegrityError):
            session.commit()
