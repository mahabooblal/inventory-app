def test_login_success(client, admin_user):
    response = client.post(
        '/auth/login',
        data={'username': admin_user.username, 'password': 'password'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Login successful.' in response.data


def test_invalid_login(client):
    response = client.post(
        '/auth/login',
        data={'username': 'baduser', 'password': 'wrongpass'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Invalid username or password.' in response.data


def test_logout_redirects_to_login(client, admin_user):
    client.post(
        '/auth/login',
        data={'username': admin_user.username, 'password': 'password'},
        follow_redirects=True,
    )

    response = client.get('/auth/logout', follow_redirects=False)
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']


def test_protected_route_redirects_to_login(client):
    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']
