def test_csrf_extension_initialized(app):
    assert 'csrf' in app.extensions
    assert app.config['WTF_CSRF_ENABLED'] is False


def test_product_form_validation_requires_required_fields(manager_client, category, supplier):
    response = manager_client.post(
        '/products/add',
        data={
            'name': '',
            'sku': '',
            'barcode': '123',
            'description': 'Incomplete',
            'price': '12.50',
            'cost_price': '6.00',
            'quantity': '10',
            'low_stock_limit': '3',
            'category_id': str(category.id),
            'supplier_id': str(supplier.id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'This field is required' in response.data


def test_login_form_requires_username_and_password(client):
    response = client.post('/auth/login', data={'username': '', 'password': ''}, follow_redirects=True)
    assert response.status_code == 200
    assert b'This field is required' in response.data
