from pathlib import Path
import sqlite3


DATABASE_PATH = Path(__file__).resolve().parent / 'campusclaim.db'


def migrate_database():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_at TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES claims (claim_id),
                FOREIGN KEY (sender_id) REFERENCES users (user_id)
            )
            """
        )
        connection.commit()

    print(f'Messages table is ready in {DATABASE_PATH}.')


if __name__ == '__main__':
    migrate_database()
