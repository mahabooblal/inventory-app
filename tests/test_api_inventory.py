import json

from app.models import AuditLog, StockMovement, Warehouse, WarehouseStock


def get_access_token(client, username, password='password'):
    response = client.post(
        '/api/v1/auth/login',
        json={'username': username, 'password': password},
        content_type='application/json',
    )
    payload = json.loads(response.data)
    return payload['data']['access_token']


def create_warehouse(database, name='Main Warehouse', code='WH-1'):
    warehouse = Warehouse(name=name, code=code, address='Main location')
    database.session.add(warehouse)
    database.session.commit()
    return warehouse


def test_inventory_endpoints_return_standard_response(api_client, admin_user, database, category, supplier):
    token = get_access_token(api_client, 'admin')
    headers = {'Authorization': f'Bearer {token}'}

    warehouse = create_warehouse(database)

    response = api_client.post(
        '/api/v1/products',
        json={
            'name': 'Warehouse Item',
            'sku': 'WH-001',
            'barcode': '900100200',
            'price': 30.00,
            'cost_price': 15.00,
            'quantity': 2,
            'low_stock_limit': 5,
            'category_id': category.id,
            'supplier_id': supplier.id,
        },
        headers=headers,
    )
    assert response.status_code == 201
    product_id = json.loads(response.data)['data']['id']

    stock = WarehouseStock(product_id=product_id, warehouse_id=warehouse.id, quantity=2)
    database.session.add(stock)
    database.session.commit()

    movement = StockMovement(
        product_id=product_id,
        movement_type='incoming',
        quantity=2,
        quantity_before=0,
        quantity_after=2,
        unit_cost=15.00,
        created_by=admin_user.id,
    )
    database.session.add(movement)
    database.session.commit()

    response = api_client.get('/api/v1/inventory', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['meta']['total'] == 1
    assert data['data'][0]['product_id'] == product_id

    response = api_client.get('/api/v1/inventory/movements', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert len(data['data']) == 1
    assert data['data'][0]['product_id'] == product_id

    response = api_client.get(f'/api/v1/inventory/low-stock?filters=warehouse_id:{warehouse.id}', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['data'][0]['warehouse_id'] == warehouse.id

    response = api_client.get('/api/v1/inventory/valuation', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['data'][0]['value'] == 30.0

    viewed_audit = AuditLog.query.filter_by(action='INVENTORY_VIEWED', user_id=admin_user.id).first()
    assert viewed_audit is not None
    assert viewed_audit.result == 'success'

    low_stock_audit = AuditLog.query.filter_by(action='LOW_STOCK_VIEWED', user_id=admin_user.id).first()
    assert low_stock_audit is not None
    assert low_stock_audit.result == 'success'

    valuation_audit = AuditLog.query.filter_by(action='INVENTORY_VALUATION_VIEWED', user_id=admin_user.id).first()
    assert valuation_audit is not None
    assert valuation_audit.result == 'success'


def test_inventory_search_and_filtering(api_client, admin_user, database, category, supplier):
    token = get_access_token(api_client, 'admin')
    headers = {'Authorization': f'Bearer {token}'}

    warehouse_1 = create_warehouse(database, name='Warehouse One', code='W1')
    warehouse_2 = create_warehouse(database, name='Warehouse Two', code='W2')

    product_a = api_client.post(
        '/api/v1/products',
        json={
            'name': 'First Item',
            'sku': 'FI-001',
            'barcode': '101010101',
            'price': 5.00,
            'cost_price': 2.00,
            'quantity': 1,
            'low_stock_limit': 5,
            'category_id': category.id,
            'supplier_id': supplier.id,
        },
        headers=headers,
    )
    product_b = api_client.post(
        '/api/v1/products',
        json={
            'name': 'Second Item',
            'sku': 'SI-002',
            'barcode': '202020202',
            'price': 10.00,
            'cost_price': 4.00,
            'quantity': 10,
            'low_stock_limit': 2,
            'category_id': category.id,
            'supplier_id': supplier.id,
        },
        headers=headers,
    )

    product_a_id = json.loads(product_a.data)['data']['id']
    product_b_id = json.loads(product_b.data)['data']['id']

    database.session.add(WarehouseStock(product_id=product_a_id, warehouse_id=warehouse_1.id, quantity=1))
    database.session.add(WarehouseStock(product_id=product_b_id, warehouse_id=warehouse_2.id, quantity=10))
    database.session.commit()

    response = api_client.get('/api/v1/inventory?q=First', headers=headers)
    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['success'] is True
    assert len(data['data']) == 1
    assert data['data'][0]['product_name'] == 'First Item'

    response = api_client.get(f'/api/v1/inventory?filters=warehouse_id:{warehouse_2.id}', headers=headers)
    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['success'] is True
    assert all(item['warehouse_id'] == warehouse_2.id for item in data['data'])


def test_inventory_movements_date_filter_and_validation(api_client, admin_user, database, category, supplier):
    token = get_access_token(api_client, 'admin')
    headers = {'Authorization': f'Bearer {token}'}

    product = api_client.post(
        '/api/v1/products',
        json={
            'name': 'Date Filter Item',
            'sku': 'DF-001',
            'barcode': '303030303',
            'price': 12.00,
            'cost_price': 6.00,
            'quantity': 5,
            'low_stock_limit': 1,
            'category_id': category.id,
            'supplier_id': supplier.id,
        },
        headers=headers,
    )
    product_id = json.loads(product.data)['data']['id']

    database.session.add(WarehouseStock(product_id=product_id, warehouse_id=create_warehouse(database).id, quantity=5))
    database.session.add(StockMovement(
        product_id=product_id,
        movement_type='incoming',
        quantity=5,
        quantity_before=0,
        quantity_after=5,
        unit_cost=6.00,
        created_by=admin_user.id,
    ))
    database.session.commit()

    response = api_client.get('/api/v1/inventory/movements?start_date=2000-01-01T00:00:00&end_date=2099-12-31T23:59:59', headers=headers)
    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['success'] is True
    assert len(data['data']) >= 1

    response = api_client.get(f'/api/v1/inventory/movements?filters=movement_type:incoming,product_id:{product_id}&q=Date', headers=headers)
    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['success'] is True
    assert all(item['movement_type'] == 'incoming' for item in data['data'])

    response = api_client.get('/api/v1/inventory/movements?start_date=not-a-date', headers=headers)
    data = json.loads(response.data)
    assert response.status_code == 400
    assert data['success'] is False
    assert data['error']['code'] == 'INVALID_DATE_FILTER'


def test_inventory_low_stock_global_and_valuation_filters(api_client, admin_user, database, category, supplier):
    token = get_access_token(api_client, 'admin')
    headers = {'Authorization': f'Bearer {token}'}

    product = api_client.post(
        '/api/v1/products',
        json={
            'name': 'Global Low Stock',
            'sku': 'GLS-001',
            'barcode': '909090909',
            'price': 8.00,
            'cost_price': 4.00,
            'quantity': 1,
            'low_stock_limit': 5,
            'category_id': category.id,
            'supplier_id': supplier.id,
        },
        headers=headers,
    )
    product_id = json.loads(product.data)['data']['id']

    warehouse = create_warehouse(database, name='Value Warehouse', code='VW-1')
    database.session.add(WarehouseStock(product_id=product_id, warehouse_id=warehouse.id, quantity=1))
    database.session.commit()

    response = api_client.get('/api/v1/inventory/low-stock', headers=headers)
    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['success'] is True
    assert any(item['product_id'] == product_id and item['warehouse_id'] is None for item in data['data'])

    response = api_client.get(
        f'/api/v1/inventory/valuation?filters=product_id:{product_id},warehouse_id:{warehouse.id}&start_date=2000-01-01T00:00:00&end_date=2099-12-31T23:59:59',
        headers=headers,
    )
    data = json.loads(response.data)
    assert response.status_code == 200
    assert data['success'] is True
    assert any(item['product_id'] == product_id for item in data['data'])
