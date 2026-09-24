import sqlite3

import pytest

import app as app_module


SCHEMA = """
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    report_type TEXT NOT NULL,
    location TEXT NOT NULL,
    date_lost_found DATE NOT NULL,
    verification_question TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE TABLE claims (
    claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    claimant_id INTEGER NOT NULL,
    verification_answer TEXT NOT NULL,
    additional_message TEXT,
    claim_status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items (item_id),
    FOREIGN KEY (claimant_id) REFERENCES users (user_id)
);
"""


@pytest.fixture
def app(monkeypatch, tmp_path):
    database_path = tmp_path / 'campusclaim-test.db'
    with sqlite3.connect(database_path) as connection:
        connection.execute('PRAGMA foreign_keys = ON')
        connection.executescript(SCHEMA)

    monkeypatch.setattr(app_module, 'DATABASE_PATH', database_path)
    app_module.app.config.update(TESTING=True)
    yield app_module.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def database_path(app):
    return app_module.DATABASE_PATH