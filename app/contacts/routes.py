import csv
import io
import json

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app.contacts.forms import BulkImportForm, ContactForm
from app.services.contact_service import ContactNotFoundError, ContactService, DuplicateContactError

contacts_bp = Blueprint("contacts", __name__)


def _service():
    return ContactService(current_user)


@contacts_bp.route("/")
@login_required
def index():
    service = _service()
    query = request.args.get("q", "").strip()
    contacts = service.search_contacts(query) if query else service.list_contacts()
    return render_template("contacts/index.html", contacts=contacts, query=query)


@contacts_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    form = ContactForm()
    if form.validate_on_submit():
        try:
            result = _service().add_contact(form.name.data, form.email.data)
            session["last_action"] = result
            flash(f"Added {form.name.data}.", "success")
            return redirect(url_for("contacts.index"))
        except DuplicateContactError as error:
            form.email.errors.append(str(error))
    return render_template("contacts/form.html", form=form, title="Add contact")


@contacts_bp.route("/edit/<int:contact_id>", methods=["GET", "POST"])
@login_required
def edit(contact_id):
    service = _service()
    try:
        contact = service.get_contact(contact_id)
    except ContactNotFoundError:
        abort(404)

    form = ContactForm(obj=contact)
    if form.validate_on_submit():
        try:
            result = service.update_contact(contact_id, form.name.data, form.email.data)
            session["last_action"] = result
            flash(f"Updated {form.name.data}.", "success")
            return redirect(url_for("contacts.index"))
        except DuplicateContactError as error:
            form.email.errors.append(str(error))
    return render_template("contacts/form.html", form=form, title="Edit contact")


@contacts_bp.route("/delete/<int:contact_id>", methods=["POST"])
@login_required
def delete(contact_id):
    try:
        result = _service().delete_contact(contact_id)
    except ContactNotFoundError:
        abort(404)
    session["last_action"] = result
    flash("Contact deleted.", "success")
    return redirect(url_for("contacts.index"))


@contacts_bp.route("/undo", methods=["POST"])
@login_required
def undo():
    last_action = session.pop("last_action", None)
    if last_action is None:
        flash("Nothing to undo.", "info")
    else:
        _service().undo(last_action)
        flash("Last action undone.", "success")
    return redirect(url_for("contacts.index"))


@contacts_bp.route("/import", methods=["GET", "POST"])
@login_required
def bulk_import():
    form = BulkImportForm()
    if form.validate_on_submit():
        rows = _parse_bulk_input(form.data.data)
        result = _service().bulk_import(rows)
        flash(
            f"Imported {len(result['added'])} contact(s), "
            f"skipped {len(result['skipped'])} duplicate(s).",
            "success",
        )
        return redirect(url_for("contacts.index"))
    return render_template("contacts/import.html", form=form)


@contacts_bp.route("/export/<fmt>")
@login_required
def export(fmt):
    contacts = _service().list_contacts()

    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Name", "Email"])
        for contact in contacts:
            writer.writerow([contact.name, contact.email])
        return Response(
            buffer.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=contacts.csv"},
        )

    if fmt == "json":
        data = [{"name": c.name, "email": c.email} for c in contacts]
        return Response(
            json.dumps(data, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=contacts.json"},
        )

    abort(404)


def _parse_bulk_input(raw_text):
    """Turns pasted "Name,Email" lines into (name, email) tuples,
    silently skipping blank lines and malformed ones."""
    rows = []
    for line in raw_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2 and parts[0] and parts[1]:
            rows.append((parts[0], parts[1]))
    return rows
