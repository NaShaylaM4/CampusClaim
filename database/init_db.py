from pathlib import Path
import sqlite3


DATABASE_PATH = Path(__file__).resolve().parent / 'campusclaim.db'


def initialize_database():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute('PRAGMA foreign_keys = ON')
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS items (
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

            CREATE TABLE IF NOT EXISTS claims (
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
        )

    print(f'Database and tables created successfully at {DATABASE_PATH}')


if __name__ == '__main__':
    initialize_database()
