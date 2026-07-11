# ContactVault v2.0 (Web)

A multi-user contact manager built with Flask — the web counterpart to
[ContactVault v1.0.0](https://github.com/) (desktop, CustomTkinter + JSON).

Sign in with Google, then add, search, edit, and delete contacts with the
same case-insensitive duplicate detection, bulk CSV import, export, and
undo-last-action behavior as the desktop version — now per-user and in the
browser.

## Status

Under active development. This README will be filled in fully once the
core features are implemented and tested.

## Tech stack

- **Flask** — web framework
- **SQLAlchemy + Flask-Migrate (Alembic)** — ORM and database migrations
- **SQLite** — local database, zero setup (SQLAlchemy makes this
  swappable for PostgreSQL later with no code changes)
- **Flask-Login** — session management
- **Authlib** — Google OAuth ("Continue with Google")
- **Flask-WTF** — forms and CSRF protection
- **pytest** — test suite

## Running it locally

```bash
git clone <this-repo-url>
cd contactvault-v2
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: set SECRET_KEY to any random string, and add your own
# Google OAuth credentials (see below)

flask db upgrade                # creates instance/contactvault.db
flask run
```

Then open `http://localhost:5000`.

### Setting up your own Google OAuth credentials

Since this repo is public, Google login requires each person running it
locally to use their own free credentials (client secrets can't be
committed to a public repo):

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create an OAuth 2.0 Client ID (Web application)
3. Add `http://localhost:5000/auth/google/callback` as an authorized redirect URI
4. Copy the client ID and secret into your `.env` file

## Running tests

```bash
pytest
```

## License

MIT — see [LICENSE](LICENSE).
