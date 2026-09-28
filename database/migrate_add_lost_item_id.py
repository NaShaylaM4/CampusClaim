from pathlib import Path
import os
import sqlite3


DATABASE_PATH = Path(
    os.environ.get('DATABASE_PATH', Path(__file__).resolve().parent / 'campusclaim.db')
)


def migrate_database():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute('PRAGMA foreign_keys = ON')
        columns = connection.execute('PRAGMA table_info(claims)').fetchall()
        column_names = {column[1] for column in columns}
        if 'lost_item_id' in column_names:
            print('Migration not needed: claims.lost_item_id already exists.')
            return

        connection.execute(
            'ALTER TABLE claims '
            'ADD COLUMN lost_item_id INTEGER REFERENCES items(item_id);'
        )
        connection.commit()
        print('Migration applied: added claims.lost_item_id.')


if __name__ == '__main__':
    migrate_database()
