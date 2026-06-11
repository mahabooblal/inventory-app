import json

from app.models import AuditLog, Product, StockTransfer, Warehouse, WarehouseStock


def get_access_token(client, username, password='password'):
    response = client.post(
        '/api/v1/auth/login',
        json={'username': username, 'password': password},
        content_type='application/json',
    )
    payload = json.loads(response.data)
    return payload['data']['access_token']


def test_warehouse_crud_and_inventory(api_client, admin_user, category, supplier, product, database):
    token = get_access_token(api_client, 'admin')
    headers = {'Authorization': f'Bearer {token}'}

    response = api_client.post(
        '/api/v1/warehouses',
        json={'name': 'Main Depot', 'code': 'MD-01', 'address': '100 Warehouse Lane'},
        headers=headers,
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    warehouse_id = data['data']['id']
    assert data['data']['code'] == 'MD-01'

    created_audit = AuditLog.query.filter_by(action='WAREHOUSE_CREATED', target=f'warehouse:{warehouse_id}', user_id=admin_user.id).first()
    assert created_audit is not None
    assert created_audit.result == 'success'

    # Add inventory and stock transfer records for warehouse reporting
    warehouse = Warehouse.query.get(warehouse_id)
    destination = Warehouse(name='Secondary Depot', code='SD-02', address='200 Warehouse Lane')
    database.session.add(destination)
    database.session.commit()

    stock_entry = WarehouseStock(warehouse_id=warehouse_id, product_id=product.id, quantity=8)
    database.session.add(stock_entry)
    database.session.commit()

    transfer = StockTransfer(
        transfer_number='TR-001',
        product_id=product.id,
        source_warehouse_id=warehouse_id,
        destination_warehouse_id=destination.id,
        quantity=5,
        status='completed',
    )
    database.session.add(transfer)
    database.session.commit()

    response = api_client.get(f'/api/v1/warehouses/{warehouse_id}', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['data']['name'] == 'Main Depot'

    response = api_client.get('/api/v1/warehouses', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert any(item['id'] == warehouse_id for item in data['data'])

    response = api_client.get(f'/api/v1/warehouses/{warehouse_id}/inventory', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert any(item['product_id'] == product.id for item in data['data'])

    response = api_client.get(f'/api/v1/warehouses/{warehouse_id}/movements', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert any(item['id'] == transfer.id for item in data['data'])

    response = api_client.put(
        f'/api/v1/warehouses/{warehouse_id}',
        json={'address': '101 Revised Lane', 'is_active': False},
        headers=headers,
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['data']['address'] == '101 Revised Lane'
    assert data['data']['is_active'] is False

    updated_audit = AuditLog.query.filter_by(action='WAREHOUSE_UPDATED', target=f'warehouse:{warehouse_id}', user_id=admin_user.id).first()
    assert updated_audit is not None
    assert updated_audit.result == 'success'

    response = api_client.delete(f'/api/v1/warehouses/{warehouse_id}', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['data']['deleted'] == warehouse_id

    deleted_audit = AuditLog.query.filter_by(action='WAREHOUSE_DELETED', target=f'warehouse:{warehouse_id}', user_id=admin_user.id).first()
    assert deleted_audit is not None
    assert deleted_audit.result == 'success'

    response = api_client.get(f'/api/v1/warehouses/{warehouse_id}', headers=headers)
    assert response.status_code == 404


def test_warehouse_permissions_and_validation(api_client, manager_user, staff_user, category, supplier):
    manager_token = get_access_token(api_client, 'manager')
    staff_token = get_access_token(api_client, 'staff')

    response = api_client.post(
        '/api/v1/warehouses',
        json={'name': 'Small Depot'},
        headers={'Authorization': f'Bearer {manager_token}'},
    )
    assert response.status_code == 400

    response = api_client.post(
        '/api/v1/warehouses',
        json={'name': 'Small Depot', 'code': 'SD-03'},
        headers={'Authorization': f'Bearer {staff_token}'},
    )
    assert response.status_code == 403

    response = api_client.post(
        '/api/v1/warehouses',
        json={'name': 'Small Depot', 'code': 'SD-03'},
        headers={'Authorization': f'Bearer {manager_token}'},
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    warehouse_id = data['data']['id']

    response = api_client.delete(f'/api/v1/warehouses/{warehouse_id}', headers={'Authorization': f'Bearer {manager_token}'})
    assert response.status_code == 403


def test_warehouse_search_filter_sort_pagination_and_error_paths(api_client, admin_user, category, supplier, product, database):
    token = get_access_token(api_client, 'admin')
    headers = {'Authorization': f'Bearer {token}'}

    warehouse_ids = []
    for name, code in [
        ('North Depot', 'ND-01'),
        ('East Depot', 'ED-02'),
        ('West Depot', 'WD-03'),
    ]:
        response = api_client.post(
            '/api/v1/warehouses',
            json={'name': name, 'code': code, 'address': f'{code} Address'},
            headers=headers,
        )
        assert response.status_code == 201
        warehouse_ids.append(json.loads(response.data)['data']['id'])

    response = api_client.put(
        f'/api/v1/warehouses/{warehouse_ids[2]}',
        json={'is_active': False},
        headers=headers,
    )
    assert response.status_code == 200

    response = api_client.get('/api/v1/warehouses?q=Depot&sort_by=code&sort_order=asc&page=1&per_page=2', headers=headers)
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload['meta']['page'] == 1
    assert payload['meta']['per_page'] == 2
    assert payload['meta']['total'] >= 3
    assert len(payload['data']) == 2

    response = api_client.get('/api/v1/warehouses?filters=code:ED-02', headers=headers)
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert len(payload['data']) == 1
    assert payload['data'][0]['code'] == 'ED-02'

    response = api_client.get('/api/v1/warehouses?filters=is_active:false', headers=headers)
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert all(item['is_active'] is False for item in payload['data'])

    warehouse_id = warehouse_ids[0]
    destination = Warehouse(name='Secondary Depot', code='SD-05', address='200 Warehouse Lane')
    database.session.add(destination)
    database.session.commit()

    stock_entry = WarehouseStock(warehouse_id=warehouse_id, product_id=product.id, quantity=8)
    database.session.add(stock_entry)
    database.session.commit()

    transfer = StockTransfer(
        transfer_number='TR-SEARCH-001',
        product_id=product.id,
        source_warehouse_id=warehouse_id,
        destination_warehouse_id=destination.id,
        quantity=2,
        status='completed',
    )
    database.session.add(transfer)
    database.session.commit()

    response = api_client.get(f'/api/v1/warehouses/{warehouse_id}/inventory?q={product.name}', headers=headers)
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert any(item['product_id'] == product.id for item in payload['data'])

    response = api_client.get(f'/api/v1/warehouses/{warehouse_id}/movements?filters=status:completed&q={product.sku}', headers=headers)
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert any(item['status'] == 'completed' for item in payload['data'])

    response = api_client.get('/api/v1/warehouses/999999', headers=headers)
    assert response.status_code == 404

    response = api_client.put('/api/v1/warehouses/999999', json={'name': 'Does Not Exist'}, headers=headers)
    assert response.status_code == 404

    response = api_client.delete('/api/v1/warehouses/999999', headers=headers)
    assert response.status_code == 404

    response = api_client.get('/api/v1/warehouses/999999/inventory', headers=headers)
    assert response.status_code == 404

    response = api_client.get('/api/v1/warehouses/999999/movements', headers=headers)
    assert response.status_code == 404

    response = api_client.put(
        f'/api/v1/warehouses/{warehouse_id}',
        json={},
        headers=headers,
    )
    assert response.status_code == 400
