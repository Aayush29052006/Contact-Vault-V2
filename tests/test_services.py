import pytest

from app.models.user import User
from app.services.contact_service import (
    ContactService,
    DuplicateContactError,
    ContactNotFoundError,
)


@pytest.fixture
def user(session):
    u = User(google_id="google-1", email="owner@example.com", name="Owner")
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def other_user(session):
    u = User(google_id="google-2", email="other@example.com", name="Other")
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def service(user):
    return ContactService(user)


class TestAddContact:
    def test_add_contact_succeeds(self, service):
        result = service.add_contact("Rohan Sharma", "rohan@example.com")
        assert result["action"] == "add"

        contacts = service.list_contacts()
        assert len(contacts) == 1
        assert contacts[0].name == "Rohan Sharma"

    def test_add_duplicate_email_raises(self, service):
        service.add_contact("Rohan Sharma", "rohan@example.com")
        with pytest.raises(DuplicateContactError):
            service.add_contact("Different Name", "Rohan@Example.com")

    def test_add_contact_with_blank_name_derives_from_email(self, service):
        service.add_contact("", "jane.doe@example.com")
        contact = service.list_contacts()[0]
        assert contact.name == "Jane Doe"

    def test_add_contact_with_whitespace_only_name_derives_from_email(self, service):
        service.add_contact("   ", "bob-jones@example.com")
        contact = service.list_contacts()[0]
        assert contact.name == "Bob Jones"


class TestUpdateContact:
    def test_update_contact_succeeds(self, service):
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        service.update_contact(added["contact_id"], "Rohan S.", "rohan.s@example.com")

        contact = service.get_contact(added["contact_id"])
        assert contact.name == "Rohan S."
        assert contact.email == "rohan.s@example.com"

    def test_update_to_another_contacts_email_raises(self, service):
        service.add_contact("Contact A", "a@example.com")
        added_b = service.add_contact("Contact B", "b@example.com")

        with pytest.raises(DuplicateContactError):
            service.update_contact(added_b["contact_id"], "Contact B", "A@Example.com")

    def test_update_keeping_own_email_does_not_raise(self, service):
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        # Editing name but keeping the same email should NOT be flagged
        # as a duplicate of itself.
        service.update_contact(added["contact_id"], "Rohan S.", "rohan@example.com")

    def test_update_nonexistent_contact_raises(self, service):
        with pytest.raises(ContactNotFoundError):
            service.update_contact(999, "Nobody", "nobody@example.com")

    def test_update_with_blank_name_derives_from_email(self, service):
        added = service.add_contact("Original Name", "rohan@example.com")
        service.update_contact(added["contact_id"], "", "priya.patel@example.com")

        contact = service.get_contact(added["contact_id"])
        assert contact.name == "Priya Patel"


class TestDeleteContact:
    def test_delete_contact_succeeds(self, service):
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        service.delete_contact(added["contact_id"])
        assert service.list_contacts() == []

    def test_delete_nonexistent_contact_raises(self, service):
        with pytest.raises(ContactNotFoundError):
            service.delete_contact(999)


class TestSearchContacts:
    def test_search_matches_name_case_insensitively(self, service):
        service.add_contact("Rohan Sharma", "rohan@example.com")
        service.add_contact("Priya Patel", "priya@example.com")

        results = service.search_contacts("rohan")
        assert len(results) == 1
        assert results[0].name == "Rohan Sharma"

    def test_search_matches_email(self, service):
        service.add_contact("Rohan Sharma", "rohan@example.com")
        results = service.search_contacts("EXAMPLE.COM")
        assert len(results) == 1


class TestBulkImport:
    def test_bulk_import_adds_all_new_contacts(self, service):
        rows = [("A", "a@example.com"), ("B", "b@example.com")]
        result = service.bulk_import(rows)

        assert len(result["added"]) == 2
        assert len(result["skipped"]) == 0
        assert len(service.list_contacts()) == 2

    def test_bulk_import_skips_existing_db_duplicate(self, service):
        service.add_contact("A", "a@example.com")
        result = service.bulk_import([("A Duplicate", "A@Example.com")])

        assert len(result["added"]) == 0
        assert len(result["skipped"]) == 1

    def test_bulk_import_skips_duplicate_within_same_batch(self, service):
        rows = [("A", "a@example.com"), ("A Again", "a@example.com")]
        result = service.bulk_import(rows)

        assert len(result["added"]) == 1
        assert len(result["skipped"]) == 1

    def test_bulk_import_derives_name_when_blank(self, service):
        result = service.bulk_import([("", "jane.doe@example.com")])

        assert result["added"][0]["name"] == "Jane Doe"
        contact = service.list_contacts()[0]
        assert contact.name == "Jane Doe"


class TestBulkDelete:
    def test_bulk_delete_removes_all_given_contacts(self, service):
        a = service.add_contact("A", "a@example.com")
        b = service.add_contact("B", "b@example.com")
        service.add_contact("C", "c@example.com")

        result = service.delete_bulk([a["contact_id"], b["contact_id"]])

        assert result["action"] == "bulk_delete"
        remaining = service.list_contacts()
        assert len(remaining) == 1
        assert remaining[0].name == "C"

    def test_bulk_delete_with_foreign_id_deletes_nothing(self, service, other_user):
        mine = service.add_contact("Mine", "mine@example.com")
        other_service = ContactService(other_user)
        theirs = other_service.add_contact("Theirs", "theirs@example.com")

        with pytest.raises(ContactNotFoundError):
            service.delete_bulk([mine["contact_id"], theirs["contact_id"]])

        # Atomic: nothing committed, "Mine" must still exist
        assert len(service.list_contacts()) == 1

    def test_undo_bulk_delete_restores_all_contacts(self, service):
        a = service.add_contact("A", "a@example.com")
        b = service.add_contact("B", "b@example.com")

        deleted = service.delete_bulk([a["contact_id"], b["contact_id"]])
        assert service.list_contacts() == []

        service.undo(deleted)
        names = {c.name for c in service.list_contacts()}
        assert names == {"A", "B"}


class TestUndo:
    def test_undo_add_removes_contact(self, service):
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        service.undo(added)
        assert service.list_contacts() == []

    def test_undo_edit_reverts_fields(self, service):
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        edit = service.update_contact(added["contact_id"], "Changed Name", "changed@example.com")
        service.undo(edit)

        contact = service.get_contact(added["contact_id"])
        assert contact.name == "Rohan Sharma"
        assert contact.email == "rohan@example.com"

    def test_undo_delete_recreates_contact(self, service):
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        deleted = service.delete_contact(added["contact_id"])
        service.undo(deleted)

        contacts = service.list_contacts()
        assert len(contacts) == 1
        assert contacts[0].name == "Rohan Sharma"

    def test_undo_unknown_action_raises(self, service):
        with pytest.raises(ValueError):
            service.undo({"action": "not_a_real_action"})

    def test_undo_bulk_import_removes_all_added_contacts(self, service):
        imported = service.bulk_import([("A", "a@example.com"), ("B", "b@example.com")])
        service.undo(imported)
        assert service.list_contacts() == []

    def test_undo_add_on_stale_history_when_contact_already_deleted(self, service):
        """Undoing an old 'add' from the activity log after the contact
        was already deleted some other way must not crash."""
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        service.delete_contact(added["contact_id"])

        service.undo(added)  # should not raise
        assert service.list_contacts() == []

    def test_undo_edit_on_stale_history_when_contact_already_deleted(self, service):
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        edit = service.update_contact(added["contact_id"], "New Name", "new@example.com")
        service.delete_contact(added["contact_id"])

        service.undo(edit)  # should not raise
        assert service.list_contacts() == []

    def test_undo_delete_skipped_when_email_now_conflicts(self, service):
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        deleted = service.delete_contact(added["contact_id"])
        # A new, unrelated contact now holds that same email
        service.add_contact("Someone Else", "rohan@example.com")

        service.undo(deleted)  # should not raise, and should not duplicate

        contacts = service.list_contacts()
        assert len(contacts) == 1
        assert contacts[0].name == "Someone Else"

    def test_undo_bulk_delete_partially_restores_when_one_email_conflicts(self, service):
        a = service.add_contact("A", "a@example.com")
        b = service.add_contact("B", "b@example.com")
        deleted = service.delete_bulk([a["contact_id"], b["contact_id"]])

        # Someone re-registers A's old email under a new contact before the undo
        service.add_contact("New A", "a@example.com")

        service.undo(deleted)

        names = {c.name for c in service.list_contacts()}
        assert names == {"New A", "B"}  # B restored, A's slot left alone

    def test_undo_bulk_import_partial_when_some_already_deleted(self, service):
        imported = service.bulk_import([("A", "a@example.com"), ("B", "b@example.com")])
        a_contact = next(c for c in service.list_contacts() if c.name == "A")
        service.delete_contact(a_contact.id)

        service.undo(imported)  # should not raise
        assert service.list_contacts() == []


class TestActivityLog:
    def test_add_contact_writes_activity_log(self, service):
        service.add_contact("Rohan Sharma", "rohan@example.com")
        logs = service.list_activity()
        assert len(logs) == 1
        assert "Added contact: Rohan Sharma" in logs[0].description

    def test_edit_contact_writes_activity_log(self, service):
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        service.update_contact(added["contact_id"], "Rohan S.", "rohan.s@example.com")

        logs = service.list_activity()
        assert any("Edited contact" in log.description for log in logs)

    def test_delete_contact_writes_activity_log(self, service):
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        service.delete_contact(added["contact_id"])

        logs = service.list_activity()
        assert any("Deleted contact" in log.description for log in logs)

    def test_bulk_import_writes_one_summary_log(self, service):
        service.bulk_import([("A", "a@example.com"), ("B", "b@example.com")])

        logs = service.list_activity()
        assert any("Bulk import" in log.description for log in logs)

    def test_undo_writes_activity_log(self, service):
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        service.undo(added)

        logs = service.list_activity()
        assert any("Undid" in log.description for log in logs)

    def test_original_actions_carry_undo_data(self, service):
        service.add_contact("Rohan Sharma", "rohan@example.com")
        log = service.list_activity()[0]
        assert log.undo_data is not None

        import json
        data = json.loads(log.undo_data)
        assert data["action"] == "add"

    def test_undid_entries_have_no_undo_data(self, service):
        """An 'Undid: ...' entry must not itself be undoable - that
        would open the door to undo/redo chains, which is out of scope."""
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        service.undo(added)

        undid_log = next(log for log in service.list_activity() if log.description.startswith("Undid"))
        assert undid_log.undo_data is None

    def test_activity_log_ordered_newest_first(self, service):
        service.add_contact("First", "first@example.com")
        service.add_contact("Second", "second@example.com")

        logs = service.list_activity()
        assert "Second" in logs[0].description
        assert "First" in logs[1].description

    def test_activity_log_isolated_between_users(self, service, other_user):
        service.add_contact("Rohan Sharma", "rohan@example.com")

        other_service = ContactService(other_user)
        assert other_service.list_activity() == []

    def test_activity_log_repr(self, service):
        service.add_contact("Rohan Sharma", "rohan@example.com")
        log = service.list_activity()[0]
        assert "Added contact: Rohan Sharma" in repr(log)


class TestMultiUserIsolation:
    def test_user_cannot_access_another_users_contact(self, service, other_user):
        added = service.add_contact("Rohan Sharma", "rohan@example.com")
        other_service = ContactService(other_user)

        with pytest.raises(ContactNotFoundError):
            other_service.get_contact(added["contact_id"])

    def test_same_email_allowed_across_different_users(self, service, other_user):
        service.add_contact("Rohan Sharma", "shared@example.com")
        other_service = ContactService(other_user)
        # Should NOT raise - it's a different user's contact list
        other_service.add_contact("Someone Else", "shared@example.com")
