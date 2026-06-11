from app.services.notification_service import create_notification, get_unread_count


def test_notifications_api(admin_client, admin_user):
    from app import db

    note = create_notification(admin_user.id, 'Notify test', 'info')
    second_note = create_notification(admin_user.id, 'Notify test 2', 'warning')
    db.session.commit()

    rv = admin_client.get('/notifications/recent')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['count'] == 2
    assert len(data['notifications']) >= 2

    rv = admin_client.post(f'/notifications/mark_read/{note.id}', data={}, follow_redirects=True)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['count'] == 1
    assert get_unread_count(admin_user.id) == 1

    rv = admin_client.get('/notifications/recent')
    assert rv.status_code == 200
    data = rv.get_json()
    unread_ids = {item['id'] for item in data['notifications'] if not item['is_read']}
    assert unread_ids == {second_note.id}

    rv = admin_client.post('/notifications/mark_all_read', data={}, follow_redirects=True)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['updated'] == 1
    assert data['count'] == 0

    assert get_unread_count(admin_user.id) == 0

    rv = admin_client.get('/notifications/recent')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['count'] == 0
    assert all(item['is_read'] for item in data['notifications'])
