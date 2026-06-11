import json
from urllib.parse import quote_plus

from app.models import AuditLog, Product, PurchaseOrder, Supplier


def get_access_token(client, username, password='password'):
    response = client.post(
        '/api/v1/auth/login',
        json={'username': username, 'password': password},
        content_type='application/json',
    )
    payload = json.loads(response.data)
    return payload['data']['access_token']


def test_supplier_crud_and_related_collections(api_client, admin_user, category, supplier):
    token = get_access_token(api_client, 'admin')
    headers = {'Authorization': f'Bearer {token}'}

    response = api_client.post(
        '/api/v1/suppliers',
        json={'name': 'New Vendor', 'email': 'vendor@example.com', 'phone': '555-7890', 'address': '400 Supply St'},
        headers=headers,
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    supplier_id = data['data']['id']
    assert data['data']['name'] == 'New Vendor'

    created_audit = AuditLog.query.filter_by(action='SUPPLIER_CREATED', target=f'supplier:{supplier_id}', user_id=admin_user.id).first()
    assert created_audit is not None
    assert created_audit.result == 'success'

    response = api_client.get(f'/api/v1/suppliers/{supplier_id}', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['data']['email'] == 'vendor@example.com'

    response = api_client.put(
        f'/api/v1/suppliers/{supplier_id}',
        json={'phone': '555-0001'},
        headers=headers,
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['data']['phone'] == '555-0001'

    updated_audit = AuditLog.query.filter_by(action='SUPPLIER_UPDATED', target=f'supplier:{supplier_id}', user_id=admin_user.id).first()
    assert updated_audit is not None
    assert updated_audit.result == 'success'

    product = Product(
        name='Vendor Product',
        sku='VP-001',
        barcode='999999999',
        price=18.00,
        cost_price=9.00,
        quantity=10,
        low_stock_limit=2,
        category_id=category.id,
        supplier_id=supplier_id,
    )
    purchase_order = PurchaseOrder(
        po_number='PO-001',
        supplier_id=supplier_id,
        status='ordered',
    )
    from app import db

    db.session.add(product)
    db.session.add(purchase_order)
    db.session.commit()

    response = api_client.get(f'/api/v1/suppliers/{supplier_id}/products', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert any(item['sku'] == 'VP-001' for item in data['data'])

    response = api_client.get(f'/api/v1/suppliers/{supplier_id}/purchase-orders', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert any(item['po_number'] == 'PO-001' for item in data['data'])

    response = api_client.post(
        '/api/v1/suppliers',
        json={'name': 'Delete Vendor', 'email': 'delete-vendor@example.com'},
        headers=headers,
    )
    assert response.status_code == 201
    delete_supplier_id = json.loads(response.data)['data']['id']

    response = api_client.delete(f'/api/v1/suppliers/{delete_supplier_id}', headers=headers)
    assert response.status_code == 200
    deleted_audit = AuditLog.query.filter_by(action='SUPPLIER_DELETED', target=f'supplier:{delete_supplier_id}', user_id=admin_user.id).first()
    assert deleted_audit is not None
    assert deleted_audit.result == 'success'

    response = api_client.get(f'/api/v1/suppliers/{delete_supplier_id}', headers=headers)
    assert response.status_code == 404

def test_supplier_search_filter_sort_pagination_and_error_paths(api_client, admin_user, category, supplier, database):
    token = get_access_token(api_client, 'admin')
    headers = {'Authorization': f'Bearer {token}'}

    response = api_client.post(
        '/api/v1/suppliers',
        json={'name': 'Alpha Vendor', 'email': 'alpha@example.com', 'phone': '555-0101', 'address': '100 Supply Ln'},
        headers=headers,
    )
    assert response.status_code == 201
    alpha_id = json.loads(response.data)['data']['id']

    response = api_client.post(
        '/api/v1/suppliers',
        json={'name': 'Beta Vendor', 'email': 'beta@example.com', 'phone': '555-0202', 'address': '200 Supply Ln'},
        headers=headers,
    )
    assert response.status_code == 201
    beta_id = json.loads(response.data)['data']['id']

    response = api_client.post(
        '/api/v1/suppliers',
        json={'name': 'Gamma Vendor', 'email': 'gamma@example.com', 'phone': '555-0303', 'address': '300 Supply Ln'},
        headers=headers,
    )
    assert response.status_code == 201
    gamma_id = json.loads(response.data)['data']['id']

    response = api_client.put(
        f'/api/v1/suppliers/{gamma_id}',
        json={'email': 'gamma_updated@example.com', 'phone': '555-9999', 'address': 'Updated Supply Ln', 'is_active': False},
        headers=headers,
    )
    assert response.status_code == 200

    response = api_client.get('/api/v1/suppliers?q=Vendor&filters=is_active:true&sort_by=email&sort_order=desc', headers=headers)
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert all(item['is_active'] is True for item in payload['data'])
    assert len(payload['data']) >= 2

    product = Product(
        name='Vendor Product',
        sku='VP-001',
        barcode='999999999',
        price=18.00,
        cost_price=9.00,
        quantity=10,
        low_stock_limit=2,
        category_id=category.id,
        supplier_id=alpha_id,
    )
    purchase_order = PurchaseOrder(
        po_number='PO-SEARCH-001',
        supplier_id=alpha_id,
        status='ordered',
    )
    database.session.add(product)
    database.session.add(purchase_order)
    database.session.commit()

    filters_payload = quote_plus(json.dumps({'category_id': category.id}))
    response = api_client.get(
        f'/api/v1/suppliers/{alpha_id}/products?filters={filters_payload}&q=VP-001&sort_by=sku',
        headers=headers,
    )
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert any(item['sku'] == 'VP-001' for item in payload['data'])

    response = api_client.get(
        f'/api/v1/suppliers/{alpha_id}/purchase-orders?filters=status:ordered&q=PO-SEARCH-001&sort_by=po_number',
        headers=headers,
    )
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert any(item['po_number'] == 'PO-SEARCH-001' for item in payload['data'])

    response = api_client.post(
        '/api/v1/suppliers',
        json={'name': 'No Email Vendor'},
        headers=headers,
    )
    assert response.status_code == 400

    assert api_client.get('/api/v1/suppliers/999999', headers=headers).status_code == 404
    assert api_client.get('/api/v1/suppliers/999999/products', headers=headers).status_code == 404
    assert api_client.get('/api/v1/suppliers/999999/purchase-orders', headers=headers).status_code == 404
    assert api_client.put('/api/v1/suppliers/999999', json={'name': 'None'}, headers=headers).status_code == 404
    assert api_client.delete('/api/v1/suppliers/999999', headers=headers).status_code == 404

    response = api_client.put(f'/api/v1/suppliers/{alpha_id}', json={}, headers=headers)
    assert response.status_code == 400

def test_supplier_permissions_and_validation(api_client, manager_user, staff_user, category):
    manager_token = get_access_token(api_client, 'manager')
    staff_token = get_access_token(api_client, 'staff')

    response = api_client.post(
        '/api/v1/suppliers',
        json={'name': 'Supplier A'},
        headers={'Authorization': f'Bearer {manager_token}'},
    )
    assert response.status_code == 400

    response = api_client.post(
        '/api/v1/suppliers',
        json={'name': 'Supplier A', 'email': 'supplier@example.com'},
        headers={'Authorization': f'Bearer {staff_token}'},
    )
    assert response.status_code == 403

    response = api_client.post(
        '/api/v1/suppliers',
        json={'name': 'Supplier A', 'email': 'supplier@example.com'},
        headers={'Authorization': f'Bearer {manager_token}'},
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    supplier_id = data['data']['id']

    response = api_client.put(
        f'/api/v1/suppliers/{supplier_id}',
        json={},
        headers={'Authorization': f'Bearer {manager_token}'},
    )
    assert response.status_code == 400

    response = api_client.delete(f'/api/v1/suppliers/{supplier_id}', headers={'Authorization': f'Bearer {manager_token}'})
    assert response.status_code == 403
