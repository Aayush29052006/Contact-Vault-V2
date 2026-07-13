# Changelog

## [2.0.0] — 2026-07-13

The web edition of Contact Vault — same core philosophy as the
[v1.0.0 desktop app](https://github.com/Aayush29052006/Contact-Vault)
(layered architecture, case-insensitive duplicate detection, undo),
rebuilt for the browser with Flask, multi-user support via Google OAuth,
and a full audit trail.

### Added

**Accounts & security**
- Google OAuth login ("Continue with Google") — no passwords ever stored
- Strict per-user data isolation, enforced at the service layer and
  tested explicitly (one user can never read, edit, or undo another
  user's contacts, even by guessing an id)
- App-wide CSRF protection on every state-changing route

**Contacts**
- Add, edit, delete, and search contacts by name or email
- Case-insensitive duplicate detection, enforced twice: once in the
  service layer (friendly error message) and again via a database-level
  unique index, so a duplicate can never slip through either path
- Automatic name derivation from email when the name field is left
  blank (`jane.doe@` → "Jane Doe"), matching v1.0.0's behavior
- Bulk import via pasted text, accepting either `Name, Email` or just
  an email on its own line
- Bulk delete via multi-select checkboxes, with a "select all" option
  and quick-access delete buttons at both the top and bottom of a long
  list
- CSV and JSON export

**Undo & history**
- "Undo last action" on the dashboard for the most recent change
- **Activity Log** — a permanent, timestamped record of every action,
  with human-friendly relative times ("2 minutes ago," "Yesterday")
- Per-entry undo directly from the Activity Log — reverse any past
  action individually, not just the most recent one, with automatic
  graceful handling if the data has changed too much since (a contact
  already deleted, or a new email conflict) rather than failing loudly

**Design**
- Full light/dark theme system with a toggle in the nav, remembered
  across visits via `localStorage`, defaulting to system preference on
  first visit
- Navy-and-gold "vault/ledger" identity in dark mode, steel-blue accent
  in light mode; Cormorant Garamond for headings, Outfit for UI text,
  JetBrains Mono for timestamps

**Engineering**
- Layered architecture: Flask routes → `ContactService` (all business
  logic, zero Flask imports, fully unit-testable) → SQLAlchemy models →
  SQLite, swappable to PostgreSQL with no code changes
- Alembic migrations for schema versioning
- 118 automated tests, 100% statement coverage
- CI via GitHub Actions across Ubuntu, Windows, and macOS

### Notable bugs found and fixed during development

- `ContactService.delete_bulk` originally assumed skipping `commit()`
  was enough to keep a failed batch atomic — it wasn't. SQLAlchemy's
  autoflush can push a pending delete to the database as soon as the
  next query runs, so the first contact in a batch could be deleted
  before a later one's "not found" error was even raised. Fixed with
  an explicit rollback on failure.
- A CSS `::before` pseudo-element used to draw a hover accent bar on
  table rows caused the entire row to misalign on hover in some
  browsers — pseudo-elements on `<tr>` elements are a genuine dark
  corner of CSS, since some engines generate them as anonymous table
  cells rather than true out-of-flow content. Replaced with
  `box-shadow`, which has no such risk.
- The Google OAuth redirect URI documented in the README didn't match
  the actual route (`/auth/google/callback` vs. the real
  `/auth/login/google/callback`) — caught before it caused a
  `redirect_uri_mismatch` for anyone following the setup instructions.
- Two dependencies (`requests`, `email_validator`) were missing from
  `requirements.txt` despite being required by Authlib and WTForms
  respectively — both only surfaced when running in a clean
  environment, not the development sandbox.

### Notes

- Deliberately runs localhost-only rather than deployed — anyone
  browsing the repo can clone and run it directly, matching v1.0.0's
  "just run it" accessibility.
- Kept private until after graduation, same as v1.0.0.

[Full commit history](https://github.com/Aayush29052006/Contact-Vault-V2/commits/main)
