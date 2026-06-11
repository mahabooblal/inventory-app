from app.models import User


def test_admin_can_create_user(admin_client):
    rv = admin_client.post(
        '/admin/users/new',
        data={'username': 'newadmin2', 'email': 'newadmin2@example.com', 'password': 'pass12345', 'role': 'admin'},
        follow_redirects=True,
    )
    assert rv.status_code == 200
    assert b'User created successfully' in rv.data
    assert User.query.filter_by(username='newadmin2').first() is not None


def test_admin_toggle_user_status(admin_client, database):
    user = User(username='toggleuser', email='toggle@example.com', role='staff')
    user.set_password('pass12345')
    database.session.add(user)
    database.session.commit()

    rv = admin_client.post(f'/admin/users/{user.id}/toggle', follow_redirects=True)
    assert rv.status_code == 200
    assert b'User status updated.' in rv.data
    assert User.query.get(user.id).is_active is False


def test_admin_cannot_deactivate_self(admin_client, admin_user):
    rv = admin_client.post(f'/admin/users/{admin_user.id}/toggle', follow_redirects=True)
    assert rv.status_code == 200
    assert b'You cannot deactivate your own account.' in rv.data
    assert User.query.get(admin_user.id).is_active is True


def test_admin_can_update_user_role(admin_client, database):
    user = User(username='roleuser', email='roleuser@example.com', role='staff')
    user.set_password('pass12345')
    database.session.add(user)
    database.session.commit()

    rv = admin_client.post(f'/admin/users/{user.id}/role', data={'role': 'manager'}, follow_redirects=True)
    assert rv.status_code == 200
    assert b'User role updated.' in rv.data
    assert User.query.get(user.id).role == 'manager'
