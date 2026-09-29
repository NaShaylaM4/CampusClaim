import os
import sqlite3
from pathlib import Path


POSTGRESQL_PREFIXES = ('postgres://', 'postgresql://')


def get_database_backend(database_url=None):
    if database_url is None:
        database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return 'sqlite'
    if database_url.startswith(POSTGRESQL_PREFIXES):
        return 'postgresql'
    raise ValueError('DATABASE_URL must use postgres:// or postgresql://.')


class DatabaseConnection:
    def __init__(self, connection, backend):
        self._connection = connection
        self.backend = backend

    def execute(self, query, parameters=()):
        if self.backend == 'postgresql':
            if query.strip().upper() == 'BEGIN IMMEDIATE':
                query = 'LOCK TABLE items IN SHARE ROW EXCLUSIVE MODE'
            else:
                query = query.replace('?', '%s')
        return self._connection.execute(query, parameters)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


def connect_database(database_path, database_url=None):
    if database_url is None:
        database_url = os.environ.get('DATABASE_URL')
    backend = get_database_backend(database_url)

    if backend == 'postgresql':
        import psycopg
        from psycopg.rows import dict_row

        connection = psycopg.connect(database_url, row_factory=dict_row)
    else:
        connection = sqlite3.connect(Path(database_path))
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')

    return DatabaseConnection(connection, backend)