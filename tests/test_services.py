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
