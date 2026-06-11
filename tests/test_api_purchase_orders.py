import json
from urllib.parse import quote_plus

from app.models import AuditLog


def get_access_token(client, username, password='password'):
    response = client.post(
        '/api/v1/auth/login',
        json={'username': username, 'password': password},
        content_type='application/json',
    )
    payload = json.loads(response.data)
    return payload['data']['access_token']


def test_purchase_order_crud_workflow_and_audit(client, admin_user, supplier, product, database):
    token = get_access_token(client, admin_user.username)

    create_payload = {
        'supplier_id': supplier.id,
        'expected_date': '2026-12-31',
        'notes': 'Create purchase order for inventory.',
        'items': [
            {'product_id': product.id, 'quantity_ordered': 2, 'unit_cost': 5.5},
        ],
    }

    response = client.post('/api/v1/purchase-orders', headers={'Authorization': f'Bearer {token}'}, json=create_payload)
    assert response.status_code == 201
    payload = json.loads(response.data)
    order = payload['data']
    assert order['status'] == 'draft'
    assert order['total_amount'] == 11.0
    assert order['supplier_id'] == supplier.id
    assert len(order['items']) == 1
    order_id = order['id']

    audit = AuditLog.query.filter_by(action='PO_CREATED', target=f'purchase_order:{order_id}').first()
    assert audit is not None

    update_payload = {'status': 'pending', 'notes': 'Ready for approval.'}
    response = client.put(f'/api/v1/purchase-orders/{order_id}', headers={'Authorization': f'Bearer {token}'}, json=update_payload)
    assert response.status_code == 200
    order = json.loads(response.data)['data']
    assert order['status'] == 'pending'
    assert order['notes'] == 'Ready for approval.'

    audit = AuditLog.query.filter_by(action='PO_SUBMITTED', target=f'purchase_order:{order_id}').first()
    assert audit is not None

    response = client.post(f'/api/v1/purchase-orders/{order_id}/approve', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    order = json.loads(response.data)['data']
    assert order['status'] == 'ordered'

    audit = AuditLog.query.filter_by(action='PO_APPROVED', target=f'purchase_order:{order_id}').first()
    assert audit is not None

    item_id = order['items'][0]['id']
    receive_payload = {'items': [{'item_id': item_id, 'quantity_received': 1}]}
    response = client.post(f'/api/v1/purchase-orders/{order_id}/receive', headers={'Authorization': f'Bearer {token}'}, json=receive_payload)
    assert response.status_code == 200
    order = json.loads(response.data)['data']
    assert order['status'] == 'partially_received'

    response = client.post(f'/api/v1/purchase-orders/{order_id}/receive', headers={'Authorization': f'Bearer {token}'}, json={'items': [{'item_id': item_id, 'quantity_received': 1}]})
    assert response.status_code == 200
    order = json.loads(response.data)['data']
    assert order['status'] == 'received'

    audit = AuditLog.query.filter_by(action='PO_RECEIVED', target=f'purchase_order:{order_id}').first()
    assert audit is not None


def test_purchase_order_cancel_and_invalid_transitions(client, manager_user, supplier, product, database):
    token = get_access_token(client, manager_user.username)

    payload = {
        'supplier_id': supplier.id,
        'items': [{'product_id': product.id, 'quantity_ordered': 1, 'unit_cost': 3.0}],
    }
    response = client.post('/api/v1/purchase-orders', headers={'Authorization': f'Bearer {token}'}, json=payload)
    assert response.status_code == 201
    order_id = json.loads(response.data)['data']['id']

    cancel_response = client.post(
        f'/api/v1/purchase-orders/{order_id}/cancel',
        headers={'Authorization': f'Bearer {token}'},
        json={'reason': 'Supplier no longer available'},
    )
    assert cancel_response.status_code == 200
    order = json.loads(cancel_response.data)['data']
    assert order['status'] == 'cancelled'

    response = client.post(f'/api/v1/purchase-orders/{order_id}/approve', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 403

    response = client.post(
        f'/api/v1/purchase-orders/{order_id}/receive',
        headers={'Authorization': f'Bearer {token}'},
        json={'items': [{'item_id': 9999, 'quantity_received': 1}]},
    )
    assert response.status_code == 400


def test_purchase_order_search_filter_sort_pagination(client, admin_user, supplier, product, database):
    token = get_access_token(client, admin_user.username)

    for _ in range(3):
        payload = {
            'supplier_id': supplier.id,
            'items': [{'product_id': product.id, 'quantity_ordered': 1, 'unit_cost': 1.0}],
        }
        response = client.post('/api/v1/purchase-orders', headers={'Authorization': f'Bearer {token}'}, json=payload)
        assert response.status_code == 201

    query_string = f'?page=1&per_page=2&q={quote_plus(supplier.name)}&filters=status:draft'
    response = client.get(f'/api/v1/purchase-orders{query_string}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload['meta']['page'] == 1
    assert payload['meta']['per_page'] == 2
    assert payload['meta']['total'] >= 3
    assert len(payload['data']) == 2


def test_purchase_order_requires_manager_or_admin_for_modifications(client, staff_user, supplier, product, database):
    token = get_access_token(client, staff_user.username)

    response = client.post('/api/v1/purchase-orders', headers={'Authorization': f'Bearer {token}'}, json={'supplier_id': supplier.id, 'items': [{'product_id': product.id, 'quantity_ordered': 1, 'unit_cost': 1.0}]})
    assert response.status_code == 403

    response = client.post('/api/v1/purchase-orders/1/approve', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 403


def test_purchase_order_route_not_found_and_delete_not_found(client, admin_user, supplier, product, database):
    token = get_access_token(client, admin_user.username)
    headers = {'Authorization': f'Bearer {token}'}

    response = client.get('/api/v1/purchase-orders/999999', headers=headers)
    assert response.status_code == 404
    payload = response.get_json()
    assert payload['error']['code'] == 'PURCHASE_ORDER_NOT_FOUND'

    response = client.delete('/api/v1/purchase-orders/999999', headers=headers)
    assert response.status_code == 404
    payload = response.get_json()
    assert payload['error']['code'] == 'PURCHASE_ORDER_NOT_FOUND'


def test_purchase_order_route_create_and_cancel_validation_errors(client, manager_user, supplier, product, database):
    token = get_access_token(client, manager_user.username)
    headers = {'Authorization': f'Bearer {token}'}

    response = client.post('/api/v1/purchase-orders', headers=headers, json={'items': [{'product_id': product.id, 'quantity_ordered': 1, 'unit_cost': 1.0}]})
    assert response.status_code == 400
    payload = response.get_json()
    assert 'Supplier id is required' in payload['error']['message']

    payload = {
        'supplier_id': supplier.id,
        'items': [{'product_id': product.id, 'quantity_ordered': 1, 'unit_cost': 1.0}],
    }
    create_response = client.post('/api/v1/purchase-orders', headers=headers, json=payload)
    assert create_response.status_code == 201
    order_id = json.loads(create_response.data)['data']['id']

    cancel_response = client.post(f'/api/v1/purchase-orders/{order_id}/cancel', headers=headers, json={})
    assert cancel_response.status_code == 400
    payload = cancel_response.get_json()
    assert payload['error']['code'] == 'PURCHASE_ORDER_CANCELLATION_FAILED'


def test_purchase_order_route_approve_and_receive_invalid_states(client, admin_user, manager_user, supplier, product, database):
    admin_token = get_access_token(client, admin_user.username)
    manager_token = get_access_token(client, manager_user.username)
    headers_admin = {'Authorization': f'Bearer {admin_token}'}
    headers_manager = {'Authorization': f'Bearer {manager_token}'}

    payload = {
        'supplier_id': supplier.id,
        'items': [{'product_id': product.id, 'quantity_ordered': 2, 'unit_cost': 2.5}],
    }
    create_response = client.post('/api/v1/purchase-orders', headers=headers_manager, json=payload)
    assert create_response.status_code == 201
    order_id = json.loads(create_response.data)['data']['id']

    response = client.post(f'/api/v1/purchase-orders/{order_id}/approve', headers=headers_admin)
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['error']['code'] == 'PURCHASE_ORDER_APPROVAL_FAILED'

    response = client.put(f'/api/v1/purchase-orders/{order_id}', headers=headers_manager, json={'status': 'pending'})
    assert response.status_code == 200

    approve_response = client.post(f'/api/v1/purchase-orders/{order_id}/approve', headers=headers_admin)
    assert approve_response.status_code == 200
    item_id = json.loads(approve_response.data)['data']['items'][0]['id']

    response = client.post(f'/api/v1/purchase-orders/{order_id}/receive', headers=headers_manager, json={'items': [{'item_id': item_id, 'quantity_received': 0}]})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['error']['code'] == 'PURCHASE_ORDER_RECEIVE_FAILED'

    response = client.post(f'/api/v1/purchase-orders/{order_id}/receive', headers=headers_manager, json={'items': [{'item_id': 9999, 'quantity_received': 1}]})
    assert response.status_code == 404
    payload = response.get_json()
    assert payload['error']['code'] == 'PURCHASE_ORDER_NOT_FOUND'


def test_purchase_order_route_invalid_json_and_missing_resource_errors(client, admin_user, manager_user, supplier, product, database):
    manager_token = get_access_token(client, manager_user.username)
    admin_token = get_access_token(client, admin_user.username)
    headers_manager = {'Authorization': f'Bearer {manager_token}'}
    headers_admin = {'Authorization': f'Bearer {admin_token}'}

    invalid_json_response = client.post(
        '/api/v1/purchase-orders',
        headers={'Authorization': f'Bearer {manager_token}'},
        data='not-json',
        content_type='application/json',
    )
    assert invalid_json_response.status_code == 400
    payload = invalid_json_response.get_json()
    assert payload['status'] == 'error'
    assert payload['error_code'] == 'INVALID_JSON'

    response = client.put('/api/v1/purchase-orders/999999', headers=headers_manager, json={'notes': 'no order'})
    assert response.status_code == 404
    payload = response.get_json()
    assert payload['error']['code'] == 'PURCHASE_ORDER_NOT_FOUND'

    response = client.post('/api/v1/purchase-orders/999999/approve', headers=headers_admin)
    assert response.status_code == 404
    payload = response.get_json()
    assert payload['error']['code'] == 'PURCHASE_ORDER_NOT_FOUND'

    response = client.post(
        '/api/v1/purchase-orders/999999/cancel',
        headers=headers_manager,
        data='not-json',
        content_type='application/json',
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['error']['code'] == 'VALIDATION_ERROR'


def test_purchase_order_route_service_validation_error_branches(monkeypatch, manager_user, supplier, product, database, client):
    from app.api.purchase_orders import routes as po_routes
    from app.api.utils import ValidationError

    token = get_access_token(client, manager_user.username)
    headers = {'Authorization': f'Bearer {token}'}

    def raise_validation_error(*args, **kwargs):
        raise ValidationError('Service validation failed.', errors={'items': 'invalid'})

    monkeypatch.setattr(po_routes.service, 'create_purchase_order', raise_validation_error)
    response = client.post('/api/v1/purchase-orders', headers=headers, json={'supplier_id': supplier.id, 'items': [{'product_id': product.id, 'quantity_ordered': 1, 'unit_cost': 1.0}]})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['error']['code'] == 'VALIDATION_ERROR'

    monkeypatch.setattr(po_routes.service, 'update_purchase_order', raise_validation_error)
    response = client.put('/api/v1/purchase-orders/1', headers=headers, json={'status': 'pending'})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['error']['code'] == 'VALIDATION_ERROR'

    monkeypatch.setattr(po_routes.service, 'receive_purchase_order', raise_validation_error)
    response = client.post('/api/v1/purchase-orders/1/receive', headers=headers, json={'items': [{'item_id': 1, 'quantity_received': 1}]})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['error']['code'] == 'VALIDATION_ERROR'

    monkeypatch.setattr(po_routes.service, 'cancel_purchase_order', raise_validation_error)
    response = client.post('/api/v1/purchase-orders/1/cancel', headers=headers, json={'reason': 'invalid'})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload['error']['code'] == 'VALIDATION_ERROR'
