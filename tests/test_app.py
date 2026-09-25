import sqlite3

from werkzeug.security import check_password_hash


PASSWORD = 'test-password'


def register(client, email, password=PASSWORD, first_name='Test', last_name='User'):
    return client.post(
        '/register',
        data={
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password': password,
            'confirm_password': password,
        },
        follow_redirects=True,
    )


def login(client, email, password=PASSWORD):
    return client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)


def create_item(client, report_type='LOST', title='Test Item', verification_question='What color?'):
    return client.post(
        '/items/new',
        data={
            'report_type': report_type,
            'title': title,
            'description': f'Description for {title}',
            'category': 'Electronics',
            'location': 'Library',
            'date_lost_found': '2026-09-20',
            'verification_question': verification_question if report_type == 'FOUND' else '',
        },
        follow_redirects=True,
    )


def fetch_one(database_path, query, parameters=()):
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(query, parameters).fetchone()


def fetch_value(database_path, query, parameters=()):
    return fetch_one(database_path, query, parameters)[0]


def test_register_user(client, database_path):
    response = register(client, 'alice@example.com')

    assert response.status_code == 200
    stored_password = fetch_value(
        database_path, 'SELECT password_hash FROM users WHERE email = ?', ('alice@example.com',)
    )
    assert stored_password != PASSWORD
    assert check_password_hash(stored_password, PASSWORD)


def test_duplicate_email_registration(client, database_path):
    register(client, 'alice@example.com')
    response = register(client, 'alice@example.com')

    assert response.status_code == 200
    assert b'already registered' in response.data
    assert fetch_value(database_path, 'SELECT COUNT(*) FROM users') == 1


def test_login_success(client):
    register(client, 'alice@example.com')

    response = login(client, 'alice@example.com')

    assert response.status_code == 200
    assert b'Dashboard' in response.data


def test_login_invalid_password(client):
    register(client, 'alice@example.com')

    response = login(client, 'alice@example.com', 'wrong-password')

    assert response.status_code == 200
    assert b'Invalid email or password' in response.data


def test_dashboard_requires_login(client):
    response = client.get('/dashboard')

    assert response.status_code == 302
    assert response.location.endswith('/login')


def test_how_it_works_is_public_and_explains_workflows(client):
    response = client.get('/how-it-works')

    assert response.status_code == 200
    assert b'If You Lost Something' in response.data
    assert b'If You Found Something' in response.data
    assert b'Claims are submitted only against FOUND reports.' in response.data
    assert b'CLAIM_PENDING' in response.data
    assert b'APPROVED' in response.data


def test_open_lost_item_links_to_found_items(client, database_path):
    register(client, 'alice@example.com')
    login(client, 'alice@example.com')
    create_item(client, title='Lost Keys')
    item_id = fetch_value(database_path, 'SELECT item_id FROM items WHERE title = ?', ('Lost Keys',))

    response = client.get(f'/items/{item_id}')

    assert response.status_code == 200
    assert b'Still looking for your item?' in response.data
    assert b'href="/items?report_type=FOUND"' in response.data
    assert b'Search Found Items' in response.data


def test_create_lost_item(client, database_path):
    register(client, 'alice@example.com')
    login(client, 'alice@example.com')

    response = create_item(client, title='Lost Laptop')

    assert response.status_code == 200
    item = fetch_one(database_path, 'SELECT * FROM items WHERE title = ?', ('Lost Laptop',))
    assert item['report_type'] == 'LOST'
    assert item['status'] == 'OPEN'


def test_found_item_requires_verification_question(client, database_path):
    register(client, 'alice@example.com')
    login(client, 'alice@example.com')

    response = create_item(client, report_type='FOUND', verification_question='')

    assert response.status_code == 200
    assert b'verification question is required' in response.data
    assert fetch_value(database_path, 'SELECT COUNT(*) FROM items') == 0


def test_create_found_item(client, database_path):
    register(client, 'alice@example.com')
    login(client, 'alice@example.com')

    response = create_item(client, report_type='FOUND', title='Found Wallet')

    assert response.status_code == 200
    item = fetch_one(database_path, 'SELECT * FROM items WHERE title = ?', ('Found Wallet',))
    assert item['report_type'] == 'FOUND'
    assert item['status'] == 'OPEN'


def test_user_cannot_edit_another_users_item(client, database_path):
    register(client, 'alice@example.com')
    login(client, 'alice@example.com')
    create_item(client, title='Alice Item')
    item_id = fetch_value(database_path, 'SELECT item_id FROM items WHERE title = ?', ('Alice Item',))
    client.get('/logout')

    register(client, 'bob@example.com')
    login(client, 'bob@example.com')
    response = client.post(
        f'/items/{item_id}/edit',
        data={
            'title': 'Changed by Bob',
            'description': 'Changed',
            'category': 'Electronics',
            'location': 'New Location',
            'date_lost_found': '2026-09-21',
            'verification_question': '',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'only edit your own item reports' in response.data
    assert fetch_value(database_path, 'SELECT title FROM items WHERE item_id = ?', (item_id,)) == 'Alice Item'


def test_search_items(client):
    register(client, 'alice@example.com')
    login(client, 'alice@example.com')
    create_item(client, title='Blue Backpack')
    create_item(client, title='Red Notebook')

    response = client.get('/items?q=backpack')

    assert b'Blue Backpack' in response.data
    assert b'Red Notebook' not in response.data


def test_user_cannot_claim_own_item(client, database_path):
    register(client, 'alice@example.com')
    login(client, 'alice@example.com')
    create_item(client, report_type='FOUND', title='Alice Wallet')
    item_id = fetch_value(database_path, 'SELECT item_id FROM items WHERE title = ?', ('Alice Wallet',))

    response = client.post(
        f'/items/{item_id}/claim',
        data={'verification_answer': 'Blue', 'additional_message': ''},
        follow_redirects=True,
    )

    assert b'cannot claim your own item report' in response.data
    assert fetch_value(database_path, 'SELECT COUNT(*) FROM claims') == 0


def test_user_cannot_claim_lost_item(client, database_path):
    register(client, 'alice@example.com')
    login(client, 'alice@example.com')
    create_item(client, title='Lost Keys')
    item_id = fetch_value(database_path, 'SELECT item_id FROM items WHERE title = ?', ('Lost Keys',))
    client.get('/logout')
    register(client, 'bob@example.com')
    login(client, 'bob@example.com')

    response = client.post(
        f'/items/{item_id}/claim',
        data={'verification_answer': 'Silver', 'additional_message': ''},
        follow_redirects=True,
    )

    assert b'Only found items can be claimed' in response.data
    assert fetch_value(database_path, 'SELECT COUNT(*) FROM claims') == 0


def create_found_item_for_user(client, database_path, email, title):
    register(client, email)
    login(client, email)
    create_item(client, report_type='FOUND', title=title)
    item_id = fetch_value(database_path, 'SELECT item_id FROM items WHERE title = ?', (title,))
    client.get('/logout')
    return item_id


def submit_claim(client, item_id, answer='Blue'):
    return client.post(
        f'/items/{item_id}/claim',
        data={'verification_answer': answer, 'additional_message': 'This is mine.'},
        follow_redirects=True,
    )


def test_submit_claim(client, database_path):
    item_id = create_found_item_for_user(client, database_path, 'alice@example.com', 'Found Phone')
    register(client, 'bob@example.com')
    login(client, 'bob@example.com')

    response = submit_claim(client, item_id)

    assert response.status_code == 200
    claim = fetch_one(database_path, 'SELECT * FROM claims WHERE item_id = ?', (item_id,))
    assert claim['claim_status'] == 'PENDING'
    assert fetch_value(database_path, 'SELECT status FROM items WHERE item_id = ?', (item_id,)) == 'CLAIM_PENDING'


def test_duplicate_claim_is_blocked(client, database_path):
    item_id = create_found_item_for_user(client, database_path, 'alice@example.com', 'Found Tablet')
    register(client, 'bob@example.com')
    login(client, 'bob@example.com')
    submit_claim(client, item_id)

    response = submit_claim(client, item_id, answer='Different answer')

    assert b'already submitted a claim' in response.data
    assert fetch_value(database_path, 'SELECT COUNT(*) FROM claims WHERE item_id = ?', (item_id,)) == 1


def create_claim_between_users(client, database_path, owner_email='alice@example.com', claimant_email='bob@example.com'):
    item_id = create_found_item_for_user(client, database_path, owner_email, 'Claimable Item')
    register(client, claimant_email)
    login(client, claimant_email)
    submit_claim(client, item_id)
    claim_id = fetch_value(database_path, 'SELECT claim_id FROM claims WHERE item_id = ?', (item_id,))
    client.get('/logout')
    return item_id, claim_id


def test_item_owner_can_approve_claim(client, database_path):
    item_id, claim_id = create_claim_between_users(client, database_path)
    login(client, 'alice@example.com')

    response = client.post(f'/claims/{claim_id}/approve', follow_redirects=True)

    assert response.status_code == 200
    assert fetch_value(database_path, 'SELECT claim_status FROM claims WHERE claim_id = ?', (claim_id,)) == 'APPROVED'
    assert fetch_value(database_path, 'SELECT status FROM items WHERE item_id = ?', (item_id,)) == 'CLAIM_PENDING'


def test_non_owner_cannot_approve_claim(client, database_path):
    _, claim_id = create_claim_between_users(client, database_path)
    register(client, 'charlie@example.com')
    login(client, 'charlie@example.com')

    response = client.post(f'/claims/{claim_id}/approve', follow_redirects=True)

    assert response.status_code == 200
    assert b'only review claims for your own found item reports' in response.data
    assert fetch_value(database_path, 'SELECT claim_status FROM claims WHERE claim_id = ?', (claim_id,)) == 'PENDING'


def test_reject_last_claim_reopens_item(client, database_path):
    item_id, claim_id = create_claim_between_users(client, database_path)
    login(client, 'alice@example.com')

    response = client.post(f'/claims/{claim_id}/reject', follow_redirects=True)

    assert response.status_code == 200
    assert fetch_value(database_path, 'SELECT claim_status FROM claims WHERE claim_id = ?', (claim_id,)) == 'REJECTED'
    assert fetch_value(database_path, 'SELECT status FROM items WHERE item_id = ?', (item_id,)) == 'OPEN'


def test_mark_item_returned(client, database_path):
    item_id, claim_id = create_claim_between_users(client, database_path)
    login(client, 'alice@example.com')
    client.post(f'/claims/{claim_id}/approve')

    response = client.post(f'/items/{item_id}/mark-returned', follow_redirects=True)

    assert response.status_code == 200
    assert fetch_value(database_path, 'SELECT status FROM items WHERE item_id = ?', (item_id,)) == 'RETURNED'


def test_returned_item_cannot_receive_claim(client, database_path):
    item_id, claim_id = create_claim_between_users(client, database_path)
    login(client, 'alice@example.com')
    client.post(f'/claims/{claim_id}/approve')
    client.post(f'/items/{item_id}/mark-returned')
    client.get('/logout')
    login(client, 'bob@example.com')

    response = submit_claim(client, item_id, answer='Another answer')

    assert b'no longer accepting claims' in response.data
    assert fetch_value(database_path, 'SELECT COUNT(*) FROM claims WHERE item_id = ?', (item_id,)) == 1


def test_dashboard_statistics_are_user_specific(client, database_path):
    register(client, 'alice@example.com')
    login(client, 'alice@example.com')
    create_item(client, title='Alice Lost')
    create_item(client, report_type='FOUND', title='Alice Pending Review')
    pending_review_id = fetch_value(
        database_path, 'SELECT item_id FROM items WHERE title = ?', ('Alice Pending Review',)
    )
    create_item(client, report_type='FOUND', title='Alice Returned')
    returned_id = fetch_value(database_path, 'SELECT item_id FROM items WHERE title = ?', ('Alice Returned',))
    client.get('/logout')

    bob_item_id = create_found_item_for_user(client, database_path, 'bob@example.com', 'Bob Claimable')
    login(client, 'alice@example.com')
    submit_claim(client, bob_item_id)
    client.get('/logout')

    register(client, 'charlie@example.com')
    login(client, 'charlie@example.com')
    submit_claim(client, pending_review_id)
    client.get('/logout')

    register(client, 'dana@example.com')
    login(client, 'dana@example.com')
    submit_claim(client, returned_id)
    client.get('/logout')
    login(client, 'alice@example.com')
    returned_claim_id = fetch_value(
        database_path, 'SELECT claim_id FROM claims WHERE item_id = ?', (returned_id,)
    )
    client.post(f'/claims/{returned_claim_id}/approve')
    client.post(f'/items/{returned_id}/mark-returned')

    response = client.get('/dashboard')

    assert b'<span>My Reports</span>' in response.data
    assert b'<span>Active Reports</span>' in response.data
    assert b'<span>Pending Claims</span>' in response.data
    assert b'<span>Returned Items</span>' in response.data
    assert b'<strong>3</strong>' in response.data
    assert b'<strong>2</strong>' in response.data
    assert response.data.count(b'<strong>1</strong>') == 2
    assert b'You have 1 claim' in response.data
    assert b'Bob Claimable' in response.data
    assert b'Alice Lost' in response.data
    assert b'Charlie' not in response.data


def test_pending_claim_does_not_show_contact_email(client, database_path):
    item_id, _ = create_claim_between_users(client, database_path)
    login(client, 'bob@example.com')

    response = client.get('/my-claims')

    assert response.status_code == 200
    assert b'alice@example.com' not in response.data


def test_approved_claim_shows_finder_contact(client, database_path):
    item_id, claim_id = create_claim_between_users(client, database_path)
    login(client, 'alice@example.com')
    client.post(f'/claims/{claim_id}/approve')
    login(client, 'bob@example.com')

    response = client.get('/my-claims')

    assert b'Test User' in response.data
    assert b'alice@example.com' in response.data
    assert b'Return Coordination' in response.data


def test_finder_can_see_approved_claimant_email(client, database_path):
    item_id, claim_id = create_claim_between_users(client, database_path)
    login(client, 'alice@example.com')
    client.post(f'/claims/{claim_id}/approve')

    response = client.get('/claims/received')

    assert b'bob@example.com' in response.data
    assert b'Approved Owner Contact' in response.data


def test_item_owner_can_add_return_instructions(client, database_path):
    item_id, claim_id = create_claim_between_users(client, database_path)
    login(client, 'alice@example.com')
    client.post(f'/claims/{claim_id}/approve')

    response = client.post(
        f'/claims/{claim_id}/return-instructions',
        data={'return_instructions': 'Meet at the Student Center front desk.'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Return instructions saved.' in response.data
    assert fetch_value(
        database_path,
        'SELECT return_instructions FROM claims WHERE claim_id = ?',
        (claim_id,),
    ) == 'Meet at the Student Center front desk.'


def test_non_owner_cannot_add_return_instructions(client, database_path):
    item_id, claim_id = create_claim_between_users(client, database_path)
    register(client, 'charlie@example.com')
    login(client, 'charlie@example.com')

    response = client.post(
        f'/claims/{claim_id}/return-instructions',
        data={'return_instructions': 'Unauthorized instructions'},
        follow_redirects=True,
    )

    assert b'only update return instructions for your own found item reports' in response.data
    assert fetch_value(
        database_path,
        'SELECT return_instructions FROM claims WHERE claim_id = ?',
        (claim_id,),
    ) is None


def test_pending_claim_cannot_receive_return_instructions(client, database_path):
    item_id, claim_id = create_claim_between_users(client, database_path)
    login(client, 'alice@example.com')

    response = client.post(
        f'/claims/{claim_id}/return-instructions',
        data={'return_instructions': 'Too early'},
        follow_redirects=True,
    )

    assert b'only be added to approved claims' in response.data
    assert fetch_value(
        database_path,
        'SELECT return_instructions FROM claims WHERE claim_id = ?',
        (claim_id,),
    ) is None


def test_approved_claimant_can_view_return_instructions(client, database_path):
    item_id, claim_id = create_claim_between_users(client, database_path)
    login(client, 'alice@example.com')
    client.post(f'/claims/{claim_id}/approve')
    client.post(
        f'/claims/{claim_id}/return-instructions',
        data={'return_instructions': 'Bring your student ID.'},
    )
    login(client, 'bob@example.com')

    response = client.get('/my-claims')

    assert b'Bring your student ID.' in response.data


def test_return_instructions_migration_is_idempotent(tmp_path, monkeypatch, capsys):
    from database import migrate_add_return_instructions as migration

    database_path = tmp_path / 'migration-test.db'
    with sqlite3.connect(database_path) as connection:
        connection.execute('CREATE TABLE claims (claim_id INTEGER PRIMARY KEY)')

    monkeypatch.setattr(migration, 'DATABASE_PATH', database_path)
    migration.migrate_database()
    migration.migrate_database()

    with sqlite3.connect(database_path) as connection:
        column_names = [row[1] for row in connection.execute('PRAGMA table_info(claims)')]

    output = capsys.readouterr().out
    assert 'Migration applied' in output
    assert 'already exists' in output
    assert column_names.count('return_instructions') == 1