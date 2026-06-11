def test_profile_edit_and_settings(admin_client):
    rv = admin_client.post('/profile/edit', data={'username': 'admin3', 'email': 'admin3@example.com', 'phone': '111222333', 'bio': 'Bio'}, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Profile updated successfully' in rv.data

    rv = admin_client.get('/profile/')
    assert rv.status_code == 200
    assert b'My Profile' in rv.data

    rv = admin_client.post('/profile/settings', data={'preferred_theme': 'dark', 'dashboard_density': 'compact', 'email_notifications': 'y'}, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Preferences updated successfully' in rv.data

    rv = admin_client.post('/profile/theme', data={'theme': 'light'}, follow_redirects=True)
    assert rv.status_code == 200

    rv = admin_client.post('/profile/change-password', data={'current_password': '', 'new_password': 'newpass123', 'confirm_password': 'newpass123'}, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Password changed successfully' in rv.data
