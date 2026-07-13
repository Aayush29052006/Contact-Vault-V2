from tests.conftest import login_via_google


class TestIndexRoute:
    def test_index_requires_login(self, client):
        response = client.get("/")
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_index_shows_empty_state(self, logged_in_client):
        client, _ = logged_in_client
        response = client.get("/")
        assert response.status_code == 200
        assert b"No contacts" in response.data


class TestAddRoute:
    def test_add_contact(self, logged_in_client):
        client, _ = logged_in_client
        response = client.post(
            "/add", data={"name": "Rohan Sharma", "email": "rohan@example.com"}
        )
        assert response.status_code == 302

        index = client.get("/")
        assert b"Rohan Sharma" in index.data

    def test_add_duplicate_shows_error_not_redirect(self, logged_in_client):
        client, _ = logged_in_client
        client.post("/add", data={"name": "Rohan Sharma", "email": "rohan@example.com"})
        response = client.post(
            "/add", data={"name": "Different Name", "email": "Rohan@Example.com"}
        )
        assert response.status_code == 200  # re-renders the form, doesn't redirect
        assert b"already exists" in response.data


class TestEditRoute:
    def test_edit_contact(self, logged_in_client, session):
        client, user = logged_in_client
        client.post("/add", data={"name": "Rohan Sharma", "email": "rohan@example.com"})

        from app.models.contact import Contact
        contact = Contact.query.filter_by(user_id=user.id).first()

        response = client.post(
            f"/edit/{contact.id}", data={"name": "Rohan S.", "email": "rohan.s@example.com"}
        )
        assert response.status_code == 302

        index = client.get("/")
        assert b"Rohan S." in index.data

    def test_edit_another_users_contact_returns_404(self, logged_in_client, session):
        client, user = logged_in_client
        client.post("/add", data={"name": "Rohan Sharma", "email": "rohan@example.com"})

        from app.models.contact import Contact
        contact = Contact.query.filter_by(user_id=user.id).first()

        # Log in as a completely different user in the same client session
        login_via_google(client, google_id="google-2", email="other@example.com", name="Other")
        response = client.get(f"/edit/{contact.id}")
        assert response.status_code == 404

    def test_edit_to_duplicate_email_shows_error_not_redirect(self, logged_in_client):
        client, _ = logged_in_client
        client.post("/add", data={"name": "Contact A", "email": "a@example.com"})
        client.post("/add", data={"name": "Contact B", "email": "b@example.com"})

        from app.models.contact import Contact
        contact_b = Contact.query.filter_by(email="b@example.com").first()

        response = client.post(
            f"/edit/{contact_b.id}", data={"name": "Contact B", "email": "A@Example.com"}
        )
        assert response.status_code == 200  # re-renders the form, doesn't redirect
        assert b"already exists" in response.data


class TestDeleteRoute:
    def test_delete_contact(self, logged_in_client, session):
        client, user = logged_in_client
        client.post("/add", data={"name": "Rohan Sharma", "email": "rohan@example.com"})

        from app.models.contact import Contact
        contact = Contact.query.filter_by(user_id=user.id).first()

        response = client.post(f"/delete/{contact.id}")
        assert response.status_code == 302

        index = client.get("/")
        assert b"No contacts" in index.data

    def test_delete_another_users_contact_returns_404(self, logged_in_client, session):
        client, user = logged_in_client
        client.post("/add", data={"name": "Rohan Sharma", "email": "rohan@example.com"})

        from app.models.contact import Contact
        contact = Contact.query.filter_by(user_id=user.id).first()

        login_via_google(client, google_id="google-2", email="other@example.com", name="Other")
        response = client.post(f"/delete/{contact.id}")
        assert response.status_code == 404

    def test_delete_nonexistent_contact_returns_404(self, logged_in_client):
        client, _ = logged_in_client
        response = client.post("/delete/999999")
        assert response.status_code == 404


class TestUndoRoute:
    def test_undo_after_add_removes_contact(self, logged_in_client):
        client, _ = logged_in_client
        client.post("/add", data={"name": "Rohan Sharma", "email": "rohan@example.com"})
        client.post("/undo")

        index = client.get("/")
        assert b"No contacts" in index.data

    def test_undo_with_nothing_to_undo(self, logged_in_client):
        client, _ = logged_in_client
        response = client.post("/undo")
        assert response.status_code == 302  # still redirects cleanly, just flashes a message


class TestBulkImportRoute:
    def test_import_page_loads(self, logged_in_client):
        client, _ = logged_in_client
        response = client.get("/import")
        assert response.status_code == 200
        assert b"Bulk Import" in response.data

    def test_bulk_import_adds_contacts(self, logged_in_client):
        client, _ = logged_in_client
        response = client.post(
            "/import", data={"data": "Rohan,rohan@example.com\nPriya,priya@example.com"}
        )
        assert response.status_code == 302

        index = client.get("/")
        assert b"Rohan" in index.data
        assert b"Priya" in index.data

    def test_bulk_import_skips_blank_lines(self, logged_in_client):
        client, _ = logged_in_client
        response = client.post(
            "/import",
            data={"data": "Rohan,rohan@example.com\n\n\nPriya,priya@example.com\n"},
        )
        assert response.status_code == 302

        index = client.get("/")
        assert b"Rohan" in index.data
        assert b"Priya" in index.data


class TestActivityRoute:
    def test_activity_page_requires_login(self, client):
        response = client.get("/activity")
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_activity_page_shows_logged_actions(self, logged_in_client):
        client, _ = logged_in_client
        client.post("/add", data={"name": "Rohan Sharma", "email": "rohan@example.com"})

        response = client.get("/activity")
        assert response.status_code == 200
        assert b"Added contact: Rohan Sharma" in response.data

    def test_activity_page_empty_state(self, logged_in_client):
        client, _ = logged_in_client
        response = client.get("/activity")
        assert b"No activity yet" in response.data


class TestExportRoute:
    def test_export_csv(self, logged_in_client):
        client, _ = logged_in_client
        client.post("/add", data={"name": "Rohan Sharma", "email": "rohan@example.com"})

        response = client.get("/export/csv")
        assert response.status_code == 200
        assert response.mimetype == "text/csv"
        assert b"Rohan Sharma" in response.data

    def test_export_json(self, logged_in_client):
        client, _ = logged_in_client
        client.post("/add", data={"name": "Rohan Sharma", "email": "rohan@example.com"})

        response = client.get("/export/json")
        assert response.status_code == 200
        assert response.mimetype == "application/json"
        assert b"rohan@example.com" in response.data

    def test_export_invalid_format_404s(self, logged_in_client):
        client, _ = logged_in_client
        response = client.get("/export/xml")
        assert response.status_code == 404
