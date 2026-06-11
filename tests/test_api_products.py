import json

from app.models import AuditLog, Product


def get_access_token(client, username, password='password'):
    response = client.post(
        '/api/v1/auth/login',
        json={'username': username, 'password': password},
        content_type='application/json',
    )
    payload = json.loads(response.data)
    return payload['data']['access_token']


def test_products_crud_and_standard_response(api_client, admin_user, category, supplier):
    token = get_access_token(api_client, 'admin')
    headers = {'Authorization': f'Bearer {token}'}

    create_payload = {
        'name': 'Test Product',
        'sku': 'TP-001',
        'barcode': '100200300',
        'description': 'Inventory API test product',
        'price': 12.50,
        'cost_price': 7.50,
        'quantity': 15,
        'low_stock_limit': 3,
        'category_id': category.id,
        'supplier_id': supplier.id,
    }

    response = api_client.post('/api/v1/products', json=create_payload, headers=headers)
    assert response.status_code == 201

    data = json.loads(response.data)
    assert data['success'] is True
    assert data['data']['sku'] == 'TP-001'
    product_id = data['data']['id']
    created_audit = AuditLog.query.filter_by(action='PRODUCT_CREATED', target=f'product:{product_id}', user_id=admin_user.id).first()
    assert created_audit is not None
    assert created_audit.result == 'success'

    response = api_client.get('/api/v1/products', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['meta']['page'] == 1
    assert any(item['id'] == product_id for item in data['data'])

    response = api_client.get(f'/api/v1/products/{product_id}', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['data']['name'] == 'Test Product'

    update_payload = {'name': 'Test Product Updated', 'price': 14.99}
    response = api_client.put(f'/api/v1/products/{product_id}', json=update_payload, headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['data']['name'] == 'Test Product Updated'
    assert data['data']['price'] == 14.99
    updated_audit = AuditLog.query.filter_by(action='PRODUCT_UPDATED', target=f'product:{product_id}', user_id=admin_user.id).first()
    assert updated_audit is not None
    assert updated_audit.result == 'success'

    response = api_client.delete(f'/api/v1/products/{product_id}', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['data']['deleted'] is True
    deleted_audit = AuditLog.query.filter_by(action='PRODUCT_DELETED', target=f'product:{product_id}', user_id=admin_user.id).first()
    assert deleted_audit is not None
    assert deleted_audit.result == 'success'

    response = api_client.get(f'/api/v1/products/{product_id}', headers=headers)
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['error']['code'] == 'PRODUCT_NOT_FOUND'


def test_product_permissions_and_validation(api_client, manager_user, staff_user, category, supplier):
    manager_token = get_access_token(api_client, 'manager')
    staff_token = get_access_token(api_client, 'staff')

    invalid_payload = {'name': 'Invalid Product', 'price': 9.99}
    response = api_client.post(
        '/api/v1/products',
        json=invalid_payload,
        headers={'Authorization': f'Bearer {manager_token}'},
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['error']['code'] == 'VALIDATION_FAILED'

    response = api_client.post(
        '/api/v1/products',
        json={
            'name': 'Staff Product',
            'sku': 'SP-001',
            'price': 5.00,
            'category_id': category.id,
            'supplier_id': supplier.id,
        },
        headers={'Authorization': f'Bearer {staff_token}'},
    )
    assert response.status_code == 403
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['error']['code'] == 'FORBIDDEN'


def test_product_search_and_sort(api_client, admin_user, category, supplier, product):
    token = get_access_token(api_client, 'admin')
    headers = {'Authorization': f'Bearer {token}'}

    response = api_client.post(
        '/api/v1/products',
        json={
            'name': 'Another Gadget',
            'sku': 'TP-002',
            'barcode': '200300400',
            'price': 20.00,
            'cost_price': 10.00,
            'quantity': 2,
            'low_stock_limit': 1,
            'category_id': category.id,
            'supplier_id': supplier.id,
        },
        headers=headers,
    )
    assert response.status_code == 201

    response = api_client.get('/api/v1/products?q=Gadget&sort_by=sku&sort_order=desc', headers=headers)
    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['success'] is True
    assert isinstance(data['data'], list)
    assert all('sku' in item for item in data['data'])


def test_product_duplicate_sku_and_not_found_errors(api_client, admin_user, category, supplier):
    token = get_access_token(api_client, 'admin')
    headers = {'Authorization': f'Bearer {token}'}

    response = api_client.post(
        '/api/v1/products',
        json={
            'name': 'Duplicate SKU Item',
            'sku': 'DUP-001',
            'barcode': '555555555',
            'price': 20.00,
            'cost_price': 10.00,
            'quantity': 1,
            'low_stock_limit': 1,
            'category_id': category.id,
            'supplier_id': supplier.id,
        },
        headers=headers,
    )
    assert response.status_code == 201

    response = api_client.post(
        '/api/v1/products',
        json={
            'name': 'Duplicate SKU Item 2',
            'sku': 'DUP-001',
            'barcode': '666666666',
            'price': 22.00,
            'cost_price': 11.00,
            'quantity': 1,
            'low_stock_limit': 1,
            'category_id': category.id,
            'supplier_id': supplier.id,
        },
        headers=headers,
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['error']['code'] == 'VALIDATION_FAILED'

    product_id = json.loads(response.data)['error'].get('data', {}).get('id') if response.data else None
    response = api_client.put('/api/v1/products/999999', json={'name': 'Missing Product'}, headers=headers)
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['error']['code'] == 'PRODUCT_UPDATE_FAILED'

    response = api_client.delete('/api/v1/products/999999', headers=headers)
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['error']['code'] == 'PRODUCT_DELETE_FAILED'


def test_product_update_conflict_sku(api_client, admin_user, category, supplier):
    token = get_access_token(api_client, 'admin')
    headers = {'Authorization': f'Bearer {token}'}

    response_a = api_client.post(
        '/api/v1/products',
        json={
            'name': 'Original Item',
            'sku': 'ORIG-001',
            'barcode': '777777777',
            'price': 30.00,
            'cost_price': 15.00,
            'quantity': 3,
            'low_stock_limit': 1,
            'category_id': category.id,
            'supplier_id': supplier.id,
        },
        headers=headers,
    )
    response_b = api_client.post(
        '/api/v1/products',
        json={
            'name': 'Target Item',
            'sku': 'TGT-001',
            'barcode': '888888888',
            'price': 35.00,
            'cost_price': 17.50,
            'quantity': 4,
            'low_stock_limit': 2,
            'category_id': category.id,
            'supplier_id': supplier.id,
        },
        headers=headers,
    )
    assert response_a.status_code == 201
    assert response_b.status_code == 201
    target_id = json.loads(response_b.data)['data']['id']

    response = api_client.put(
        f'/api/v1/products/{target_id}',
        json={'sku': 'ORIG-001'},
        headers=headers,
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['error']['code'] == 'VALIDATION_FAILED'


def test_product_invalid_json_returns_api_error(api_client, manager_user):
    token = get_access_token(api_client, 'manager')
    response = api_client.post(
        '/api/v1/products',
        data='{"name": "Invalid JSON',
        content_type='application/json',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert data['error']['code'] == 'INVALID_JSON'
