from database.connection import DatabaseConnection, get_database_backend


class RecordingConnection:
    def __init__(self):
        self.query = None
        self.parameters = None

    def execute(self, query, parameters=()):
        self.query = query
        self.parameters = parameters
        return self


def test_database_backend_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)

    assert get_database_backend() == 'sqlite'


def test_database_backend_selects_postgresql_urls():
    assert get_database_backend('postgres://user:pass@host/db') == 'postgresql'
    assert get_database_backend('postgresql://user:pass@host/db') == 'postgresql'


def test_postgresql_adapter_translates_parameters_and_write_lock():
    raw_connection = RecordingConnection()
    connection = DatabaseConnection(raw_connection, 'postgresql')

    connection.execute('SELECT * FROM items WHERE item_id = ?', (42,))
    assert raw_connection.query == 'SELECT * FROM items WHERE item_id = %s'
    assert raw_connection.parameters == (42,)

    connection.execute('BEGIN IMMEDIATE')
    assert raw_connection.query == 'LOCK TABLE items IN SHARE ROW EXCLUSIVE MODE'