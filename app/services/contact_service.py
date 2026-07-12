from sqlalchemy import func, or_

from app.extensions import db
from app.models.contact import Contact


class DuplicateContactError(Exception):
    """Raised when an add/edit would create a case-insensitive duplicate
    email for this user. Mirrors the check from v1.0.0's ContactService,
    now backed by the database's own unique index as a second line of
    defense (see the Contact model)."""


class ContactNotFoundError(Exception):
    """Raised when a contact_id doesn't exist, or belongs to a
    different user. Same error either way - callers, and especially
    routes, must never be able to tell those two cases apart. Leaking
    that distinction (e.g. a different message for 'not yours' vs
    'doesn't exist') would let one user probe for the existence of
    another user's data by id."""


class ContactService:
    """Business logic for one user's contacts. Deliberately has no
    knowledge of Flask, HTTP, or sessions - it's plain Python working
    against SQLAlchemy, which is what makes it possible to unit test
    without spinning up a request context, and reusable if a CLI or
    API front-end ever gets added alongside the web routes."""

    def __init__(self, user):
        self.user = user

    def list_contacts(self):
        return self.user.contacts.order_by(Contact.name).all()

    def search_contacts(self, query):
        pattern = f"%{query.strip().lower()}%"
        return (
            Contact.query.filter(Contact.user_id == self.user.id)
            .filter(
                or_(
                    func.lower(Contact.name).like(pattern),
                    func.lower(Contact.email).like(pattern),
                )
            )
            .order_by(Contact.name)
            .all()
        )

    def get_contact(self, contact_id):
        contact = Contact.query.filter_by(id=contact_id, user_id=self.user.id).first()
        if contact is None:
            raise ContactNotFoundError(f"No contact with id {contact_id} for this user.")
        return contact

    def add_contact(self, name, email):
        if self._is_duplicate(email):
            raise DuplicateContactError(f"A contact with email '{email}' already exists.")

        contact = Contact(owner=self.user, name=name.strip(), email=email.strip())
        db.session.add(contact)
        db.session.commit()
        return {"action": "add", "contact_id": contact.id}

    def update_contact(self, contact_id, name, email):
        contact = self.get_contact(contact_id)
        if self._is_duplicate(email, exclude_id=contact_id):
            raise DuplicateContactError(f"A contact with email '{email}' already exists.")

        previous = {"name": contact.name, "email": contact.email}
        contact.name = name.strip()
        contact.email = email.strip()
        db.session.commit()
        return {"action": "edit", "contact_id": contact.id, "previous": previous}

    def delete_contact(self, contact_id):
        contact = self.get_contact(contact_id)
        snapshot = {"name": contact.name, "email": contact.email}
        db.session.delete(contact)
        db.session.commit()
        return {"action": "delete", "contact_snapshot": snapshot}

    def bulk_import(self, rows):
        """rows: iterable of (name, email) pairs, e.g. from a parsed CSV.
        Skips anything that's already a duplicate in the database *or*
        earlier in this same batch - a CSV can contain its own dupes."""
        existing_emails = {c.email.lower() for c in self.list_contacts()}
        added, skipped = [], []

        for name, email in rows:
            email_lower = email.strip().lower()
            if email_lower in existing_emails:
                skipped.append({"name": name, "email": email})
                continue

            db.session.add(Contact(owner=self.user, name=name.strip(), email=email.strip()))
            existing_emails.add(email_lower)
            added.append({"name": name, "email": email})

        db.session.commit()
        return {"added": added, "skipped": skipped}

    def undo(self, last_action):
        """Reverses whatever add_contact/update_contact/delete_contact
        just returned. The caller (a route) is responsible for holding
        onto that returned dict between requests - this method doesn't
        know or care where it came from."""
        action = last_action.get("action")

        if action == "add":
            contact = self.get_contact(last_action["contact_id"])
            db.session.delete(contact)
            db.session.commit()
        elif action == "edit":
            contact = self.get_contact(last_action["contact_id"])
            previous = last_action["previous"]
            contact.name = previous["name"]
            contact.email = previous["email"]
            db.session.commit()
        elif action == "delete":
            snapshot = last_action["contact_snapshot"]
            db.session.add(Contact(owner=self.user, name=snapshot["name"], email=snapshot["email"]))
            db.session.commit()
        else:
            raise ValueError(f"Unknown action type for undo: {action!r}")

    def _is_duplicate(self, email, exclude_id=None):
        query = Contact.query.filter(
            Contact.user_id == self.user.id,
            func.lower(Contact.email) == email.strip().lower(),
        )
        if exclude_id is not None:
            query = query.filter(Contact.id != exclude_id)
        return db.session.query(query.exists()).scalar()
