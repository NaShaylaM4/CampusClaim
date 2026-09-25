from pathlib import Path
import sqlite3


DATABASE_PATH = Path(__file__).resolve().parent / 'campusclaim.db'


def migrate_database():
    with sqlite3.connect(DATABASE_PATH) as connection:
        columns = connection.execute('PRAGMA table_info(claims)').fetchall()
        column_names = {column[1] for column in columns}
        if 'return_instructions' in column_names:
            print('Migration not needed: claims.return_instructions already exists.')
            return

        connection.execute(
            'ALTER TABLE claims ADD COLUMN return_instructions TEXT;'
        )
        connection.commit()
        print('Migration applied: added claims.return_instructions.')


if __name__ == '__main__':
    migrate_database()
