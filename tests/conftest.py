import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db


@pytest.fixture
def app():
    """A fresh Flask app, configured for testing, with tables created
    in an in-memory SQLite database that's thrown away after the test."""
    app = create_app(TestConfig)

    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def session(db):
    return db.session
