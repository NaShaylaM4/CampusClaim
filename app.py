import sqlite3
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'campusclaim-development-secret-key'
# Move the secret key to an environment variable before deployment.

DATABASE_PATH = Path(__file__).resolve().parent / 'database' / 'campusclaim.db'
CATEGORIES = [
    'Electronics',
    'Phones',
    'Keys',
    'Wallets & Purses',
    'Identification Cards',
    'Bags & Backpacks',
    'Clothing',
    'Books & School Supplies',
    'Jewelry & Accessories',
    'Water Bottles',
    'Other',
]
REPORT_TYPES = ['LOST', 'FOUND']
ITEM_STATUSES = ['OPEN', 'CLAIM_PENDING', 'RETURNED', 'CLOSED']


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def login_required(view):
    def wrapped_view(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to continue.', 'error')
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    wrapped_view.__name__ = view.__name__
    return wrapped_view


def item_form_data():
    return {
        'title': request.form.get('title', '').strip(),
        'description': request.form.get('description', '').strip(),
        'category': request.form.get('category', '').strip(),
        'report_type': request.form.get('report_type', '').strip().upper(),
        'location': request.form.get('location', '').strip(),
        'date_lost_found': request.form.get('date_lost_found', '').strip(),
        'verification_question': request.form.get('verification_question', '').strip(),
        'status': request.form.get('status', '').strip().upper() or 'OPEN',    }


def validate_item_form(item):
    required_fields = [
        item['title'], item['description'], item['category'],
        item['report_type'], item['location'], item['date_lost_found'],
    ]
    if not all(required_fields):
        return 'Please complete all required fields.'
    if item['report_type'] not in REPORT_TYPES:
        return 'Please select a valid report type.'
    if item['category'] not in CATEGORIES:
        return 'Please select a valid category.'
    if item['report_type'] == 'FOUND' and not item['verification_question']:
        return 'A verification question is required for found items.'
    if item['status'] not in ITEM_STATUSES:
        return 'Please select a valid status.'
    return None


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


@app.route('/items/new', methods=['GET', 'POST'])
@login_required
def create_item():
    item = item_form_data() if request.method == 'POST' else {
        'title': '', 'description': '', 'category': '', 'report_type': 'LOST',
        'location': '', 'date_lost_found': '', 'verification_question': '',
        'status': 'OPEN',
    }
    if request.method == 'POST':
        item['status'] = 'OPEN'  # Ensure new items are always created with 'OPEN' status
        
        error = validate_item_form(item)
        if error:
            flash(error, 'error')
            return render_template('report_item.html', item=item, categories=CATEGORIES)

        connection = get_db_connection()
        try:
            connection.execute(
                """
                INSERT INTO items (
                    user_id, title, description, category, report_type, location,
                    date_lost_found, verification_question, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
                """,
                (
                    session['user_id'], item['title'], item['description'],
                    item['category'], item['report_type'], item['location'],
                    item['date_lost_found'], item['verification_question'] or None,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        flash('Item report created successfully.', 'success')
        return redirect(url_for('my_reports'))

    return render_template('report_item.html', item=item, categories=CATEGORIES)


@app.route('/items')
def browse_items():
    query = request.args.get('q', '').strip()
    report_type = request.args.get('report_type', '').strip().upper()
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip().upper()

    filters = []
    parameters = []
    if query:
        filters.append(
            '(title LIKE ? COLLATE NOCASE OR description LIKE ? COLLATE NOCASE '
            'OR location LIKE ? COLLATE NOCASE)'
        )
        keyword = f'%{query}%'
        parameters.extend([keyword, keyword, keyword])
    if report_type in REPORT_TYPES:
        filters.append('report_type = ?')
        parameters.append(report_type)
    if category in CATEGORIES:
        filters.append('category = ?')
        parameters.append(category)
    if status in ITEM_STATUSES:
        filters.append('status = ?')
        parameters.append(status)

    sql = """
        SELECT item_id, title, report_type, category, location,
               date_lost_found, status
        FROM items
    """
    if filters:
        sql += ' WHERE ' + ' AND '.join(filters)
    sql += ' ORDER BY created_at DESC'

    connection = get_db_connection()
    try:
        items = connection.execute(sql, parameters).fetchall()
    finally:
        connection.close()

    return render_template(
        'browse_items.html',
        items=items,
        query=query,
        selected_report_type=report_type,
        selected_category=category,
        selected_status=status,
        categories=CATEGORIES,
        report_types=REPORT_TYPES,
        item_statuses=ITEM_STATUSES,
    )


@app.route('/items/<int:item_id>')
def item_details(item_id):
    connection = get_db_connection()
    try:
        item = connection.execute(
            """
            SELECT item_id, title, report_type, category, description,
                   location, date_lost_found, status
            FROM items
            WHERE item_id = ?
            """,
            (item_id,),
        ).fetchone()
    finally:
        connection.close()

    if item is None:
        flash('Item report not found.', 'error')
        return redirect(url_for('browse_items'))
    return render_template('item_details.html', item=item)


@app.route('/my-reports')
@login_required
def my_reports():
    connection = get_db_connection()
    try:
        items = connection.execute(
            """
            SELECT item_id, title, report_type, category, status, date_lost_found
            FROM items
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (session['user_id'],),
        ).fetchall()
    finally:
        connection.close()
    return render_template('my_reports.html', items=items)


@app.route('/items/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    connection = get_db_connection()
    try:
        item = connection.execute(
            'SELECT * FROM items WHERE item_id = ?', (item_id,)
        ).fetchone()
    finally:
        connection.close()

    if item is None:
        flash('Item report not found.', 'error')
        return redirect(url_for('my_reports'))
    if item['user_id'] != session['user_id']:
        flash('You can only edit your own item reports.', 'error')
        return redirect(url_for('my_reports'))

    item_data = item_form_data() if request.method == 'POST' else dict(item)
    if request.method == 'POST':
        error = validate_item_form(item_data)
        if error:
            flash(error, 'error')
            return render_template('edit_item.html', item=item_data, categories=CATEGORIES)

        connection = get_db_connection()
        try:
            connection.execute(
                """
                UPDATE items
                SET title = ?, description = ?, category = ?, report_type = ?,
                    location = ?, date_lost_found = ?, verification_question = ?,
                    status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE item_id = ? AND user_id = ?
                """,
                (
                    item_data['title'], item_data['description'], item_data['category'],
                    item_data['report_type'], item_data['location'],
                    item_data['date_lost_found'], item_data['verification_question'] or None,
                    item_data['status'], item_id, session['user_id'],
                ),
            )
            connection.commit()
        finally:
            connection.close()

        flash('Item report updated successfully.', 'success')
        return redirect(url_for('item_details', item_id=item_id))

    return render_template('edit_item.html', item=item_data, categories=CATEGORIES)


@app.route('/items/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    connection = get_db_connection()
    try:
        item = connection.execute(
            'SELECT user_id FROM items WHERE item_id = ?', (item_id,)
        ).fetchone()
        if item is None:
            flash('Item report not found.', 'error')
        elif item['user_id'] != session['user_id']:
            flash('You can only delete your own item reports.', 'error')
        else:
            connection.execute(
                'DELETE FROM items WHERE item_id = ? AND user_id = ?',
                (item_id, session['user_id']),
            )
            connection.commit()
            flash('Item report deleted successfully.', 'success')
    finally:
        connection.close()
    return redirect(url_for('my_reports'))


if __name__ == '__main__':
    app.run(debug=True)
