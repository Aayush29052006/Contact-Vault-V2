import json

from sqlalchemy import func, or_

from app.extensions import db
from app.models.activity_log import ActivityLog
from app.models.contact import Contact
from app.utils import derive_name_from_email


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

    def list_activity(self):
        return self.user.activity_logs.all()

    def add_contact(self, name, email):
        if self._is_duplicate(email):
            raise DuplicateContactError(f"A contact with email '{email}' already exists.")

        resolved_name = name.strip() or derive_name_from_email(email)
        contact = Contact(owner=self.user, name=resolved_name, email=email.strip())
        db.session.add(contact)
        db.session.flush()  # assigns contact.id without committing

        action = {"action": "add", "contact_id": contact.id}
        self._log(f"Added contact: {contact.name}", undo_data=action)
        db.session.commit()
        return action

    def update_contact(self, contact_id, name, email):
        contact = self.get_contact(contact_id)
        if self._is_duplicate(email, exclude_id=contact_id):
            raise DuplicateContactError(f"A contact with email '{email}' already exists.")

        previous = {"name": contact.name, "email": contact.email}
        contact.name = name.strip() or derive_name_from_email(email)
        contact.email = email.strip()

        action = {"action": "edit", "contact_id": contact.id, "previous": previous}
        self._log(f"Edited contact: {previous['name']} -> {contact.name}", undo_data=action)
        db.session.commit()
        return action

    def delete_contact(self, contact_id):
        contact = self.get_contact(contact_id)
        snapshot = {"name": contact.name, "email": contact.email}
        db.session.delete(contact)

        action = {"action": "delete", "contact_snapshot": snapshot}
        self._log(f"Deleted contact: {snapshot['name']}", undo_data=action)
        db.session.commit()
        return action

    def bulk_import(self, rows):
        """rows: iterable of (name, email) pairs, e.g. from a parsed CSV.
        Skips anything that's already a duplicate in the database *or*
        earlier in this same batch - a CSV can contain its own dupes."""
        existing_emails = {c.email.lower() for c in self.list_contacts()}
        added, skipped = [], []
        new_contacts = []

        for name, email in rows:
            email_lower = email.strip().lower()
            if email_lower in existing_emails:
                skipped.append({"name": name, "email": email})
                continue

            resolved_name = name.strip() or derive_name_from_email(email)
            contact = Contact(owner=self.user, name=resolved_name, email=email.strip())
            db.session.add(contact)
            new_contacts.append(contact)
            existing_emails.add(email_lower)
            added.append({"name": resolved_name, "email": email})

        db.session.flush()  # assigns ids to every new_contacts entry
        contact_ids = [c.id for c in new_contacts]

        action = {"action": "bulk_import", "contact_ids": contact_ids}
        self._log(
            f"Bulk import: added {len(added)}, skipped {len(skipped)} duplicate(s)",
            undo_data=action,
        )
        db.session.commit()
        return {"action": "bulk_import", "contact_ids": contact_ids, "added": added, "skipped": skipped}

    def delete_bulk(self, contact_ids):
        """Delete several contacts in one transaction. If any id doesn't
        belong to this user, the whole batch is rolled back explicitly -
        SQLAlchemy's autoflush means a pending delete() can reach the
        database as soon as the next query runs, even without commit(),
        so skipping commit() alone is NOT enough to guarantee atomicity."""
        snapshots = []
        try:
            for contact_id in contact_ids:
                contact = self.get_contact(contact_id)
                snapshots.append({"name": contact.name, "email": contact.email})
                db.session.delete(contact)
        except ContactNotFoundError:
            db.session.rollback()
            raise

        action = {"action": "bulk_delete", "contact_snapshots": snapshots}
        self._log(f"Bulk deleted {len(snapshots)} contact(s)", undo_data=action)
        db.session.commit()
        return action

    def undo(self, last_action):
        """Reverses whatever a mutating method returned. Callers can be
        the dashboard's session-based "last action" slot, OR a specific
        historical row from the Activity Log - undo has no way to know
        which, and doesn't need to.

        Because a historical entry might be several actions old, the
        contact it refers to may have since been edited, deleted, or
        collide on email with something newer. Rather than crash with
        an unhandled error in those cases, each branch degrades to a
        graceful no-op with its own log line. What it does NOT protect
        against: undoing an old edit can still silently overwrite a
        newer edit to the same contact, and undoing an old add can
        delete a contact that's since been renamed into something else
        entirely - both are accepted, known trade-offs of allowing
        undo on arbitrary history rather than just the most recent
        action."""
        action = last_action.get("action")

        if action == "add":
            contact = self._find_contact(last_action["contact_id"])
            if contact is not None:
                self._log(f"Undid: added contact {contact.name}")
                db.session.delete(contact)
            else:
                self._log("Undo skipped: that contact was already removed")
            db.session.commit()

        elif action == "edit":
            contact = self._find_contact(last_action["contact_id"])
            if contact is not None:
                previous = last_action["previous"]
                self._log(f"Undid: edit on contact {contact.name}")
                contact.name = previous["name"]
                contact.email = previous["email"]
            else:
                self._log("Undo skipped: that contact was already removed")
            db.session.commit()

        elif action == "delete":
            snapshot = last_action["contact_snapshot"]
            if self._is_duplicate(snapshot["email"]):
                self._log(f"Undo skipped: a contact with email '{snapshot['email']}' already exists")
            else:
                self._log(f"Undid: deletion of contact {snapshot['name']}")
                db.session.add(Contact(owner=self.user, name=snapshot["name"], email=snapshot["email"]))
            db.session.commit()

        elif action == "bulk_delete":
            snapshots = last_action["contact_snapshots"]
            restored = 0
            for snapshot in snapshots:
                if not self._is_duplicate(snapshot["email"]):
                    db.session.add(Contact(owner=self.user, name=snapshot["name"], email=snapshot["email"]))
                    restored += 1
            self._log(f"Undid: bulk deletion ({restored} of {len(snapshots)} contact(s) restored)")
            db.session.commit()

        elif action == "bulk_import":
            contact_ids = last_action["contact_ids"]
            removed = 0
            for contact_id in contact_ids:
                contact = self._find_contact(contact_id)
                if contact is not None:
                    db.session.delete(contact)
                    removed += 1
            self._log(f"Undid: bulk import ({removed} of {len(contact_ids)} contact(s) removed)")
            db.session.commit()

        else:
            raise ValueError(f"Unknown action type for undo: {action!r}")

    def _find_contact(self, contact_id):
        """Like get_contact, but returns None instead of raising - used
        by undo() since a historical action may reference a contact
        that a later action already removed."""
        return Contact.query.filter_by(id=contact_id, user_id=self.user.id).first()

    def _is_duplicate(self, email, exclude_id=None):
        query = Contact.query.filter(
            Contact.user_id == self.user.id,
            func.lower(Contact.email) == email.strip().lower(),
        )
        if exclude_id is not None:
            query = query.filter(Contact.id != exclude_id)
        return db.session.query(query.exists()).scalar()

    def _log(self, description, undo_data=None):
        db.session.add(
            ActivityLog(
                user=self.user,
                description=description,
                undo_data=json.dumps(undo_data) if undo_data else None,
            )
        )
