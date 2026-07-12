import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.contact import Contact


def make_user(**overrides):
    defaults = {"google_id": "google-123", "email": "aayush@example.com", "name": "Aayush"}
    defaults.update(overrides)
    return User(**defaults)


def make_contact(owner, **overrides):
    defaults = {"name": "Rohan Sharma", "email": "rohan@example.com"}
    defaults.update(overrides)
    return Contact(owner=owner, **defaults)


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


class TestContactModel:
    def test_create_contact_belongs_to_user(self, session):
        user = make_user()
        session.add(user)
        session.commit()

        contact = make_contact(owner=user)
        session.add(contact)
        session.commit()

        assert contact.id is not None
        assert contact.user_id == user.id
        assert contact.owner is user

    def test_user_contacts_relationship(self, session):
        user = make_user()
        session.add(user)
        session.commit()

        session.add(make_contact(owner=user, email="a@example.com"))
        session.add(make_contact(owner=user, email="b@example.com"))
        session.commit()

        assert user.contacts.count() == 2

    def test_case_insensitive_duplicate_email_blocked(self, session):
        user = make_user()
        session.add(user)
        session.commit()

        session.add(make_contact(owner=user, email="Rohan@Example.com"))
        session.commit()

        session.add(make_contact(owner=user, email="rohan@example.com", name="Different Name"))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_same_email_allowed_for_different_users(self, session):
        user1 = make_user(google_id="g1", email="user1@example.com")
        user2 = make_user(google_id="g2", email="user2@example.com")
        session.add_all([user1, user2])
        session.commit()

        session.add(make_contact(owner=user1, email="shared@example.com"))
        session.add(make_contact(owner=user2, email="shared@example.com"))
        session.commit()  # should NOT raise - different users

        assert user1.contacts.count() == 1
        assert user2.contacts.count() == 1

    def test_deleting_user_cascades_to_contacts(self, session):
        user = make_user()
        session.add(user)
        session.commit()

        session.add(make_contact(owner=user))
        session.commit()

        session.delete(user)
        session.commit()

        assert session.query(Contact).count() == 0
