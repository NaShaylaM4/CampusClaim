import sqlite3
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'campusclaim-development-secret-key'
# Move the secret key to an environment variable before deployment.

DATABASE_PATH = Path(__file__).resolve().parent / 'database' / 'campusclaim.db'


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not all([first_name, last_name, email, password, confirm_password]):
            flash('Please complete all required fields.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        connection = get_db_connection()
        try:
            existing_user = connection.execute(
                'SELECT user_id FROM users WHERE email = ?', (email,)
            ).fetchone()
            if existing_user:
                flash('That email address is already registered.', 'error')
                return render_template('register.html')

            connection.execute(
                """
                INSERT INTO users (first_name, last_name, email, password_hash)
                VALUES (?, ?, ?, ?)
                """,
                (first_name, last_name, email, generate_password_hash(password)),
            )
            connection.commit()
        finally:
            connection.close()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        connection = get_db_connection()
        try:
            user = connection.execute(
                'SELECT user_id, first_name, password_hash FROM users WHERE email = ?',
                (email,),
            ).fetchone()
        finally:
            connection.close()

        if user is None or not check_password_hash(user['password_hash'], password):
            flash('Invalid email or password.', 'error')
            return render_template('login.html')

        session['user_id'] = user['user_id']
        session['first_name'] = user['first_name']
        session['logged_in'] = True
        return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        flash('Please log in to access your dashboard.', 'error')
        return redirect(url_for('login'))

    return render_template('dashboard.html', first_name=session['first_name'])


if __name__ == '__main__':
    app.run(debug=True)
