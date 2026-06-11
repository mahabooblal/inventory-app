import pytest
from app import create_app
from config import TestingConfig


def test_403_forbidden_for_staff(staff_client):
    response = staff_client.get('/admin/users')
    assert response.status_code == 403


def test_404_renders_not_found_page(client):
    response = client.get('/this-route-does-not-exist')
    assert response.status_code == 404
    assert b'Page Not Found' in response.data


def test_500_renders_server_error_page():
    app = create_app(config_class=TestingConfig)
    app.config['TESTING'] = False
    app.config['PROPAGATE_EXCEPTIONS'] = False

    @app.route('/__test_trigger_error')
    def trigger_error():
        raise RuntimeError('Intentional test failure')

    with app.test_client() as client:
        response = client.get('/__test_trigger_error')

    assert response.status_code == 500
    assert b'Server Error' in response.data


def test_admin_only_route_requires_admin(manager_client):
    response = manager_client.get('/admin/users')
    assert response.status_code == 403


@pytest.mark.parametrize('path', ['/dashboard', '/products/', '/reports/'])
def test_login_required_for_protected_routes(client, path):
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']
