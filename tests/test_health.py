def test_health_check_alive(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert data['db'] == 'connected'


def test_customers_list_page(manager_client):
    response = manager_client.get('/customers/')
    assert response.status_code == 200
    assert b'Customers' in response.data


def test_profile_page_loads(manager_client):
    response = manager_client.get('/profile/')
    assert response.status_code == 200
    assert b'Profile' in response.data
