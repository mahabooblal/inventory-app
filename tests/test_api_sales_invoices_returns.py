import json


def get_access_token(client, username, password='password'):
    response = client.post(
        '/api/v1/auth/login',
        json={'username': username, 'password': password},
        content_type='application/json',
    )
    payload = json.loads(response.data)
    return payload['data']['access_token']


def test_api_docs_includes_sales_invoices_and_returns_endpoints(api_client):
    response = api_client.get('/api/openapi.json')
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert '/api/v1/sales' in payload['paths']
    assert '/api/v1/invoices' in payload['paths']
    assert '/api/v1/returns' in payload['paths']
    assert '/api/v1/invoices/{invoice_id}/payment' in payload['paths']
    assert '/api/v1/returns/{return_order_id}/approve' in payload['paths']


def test_api_sales_invoices_returns_workflow(client, admin_user, product, customer, database):
    token = get_access_token(client, admin_user.username)
    headers = {'Authorization': f'Bearer {token}'}

    response = client.post(
        '/api/v1/sales',
        headers=headers,
        json={
            'product_id': product.id,
            'quantity': 1,
            'selling_price': 15.0,
            'customer_id': customer.id,
            'destination_details': 'POS checkout',
        },
    )
    assert response.status_code == 201
    sale = response.get_json()['data']
    assert sale['product_id'] == product.id
    assert sale['quantity'] == 1
    assert sale['selling_price'] == 15.0

    invoice_response = client.post(
        '/api/v1/invoices',
        headers=headers,
        json={
            'customer_id': customer.id,
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 1,
                    'unit_price': 10.0,
                    'discount_amount': 0,
                    'tax_rate': 0,
                }
            ],
            'payment_amount': 5.0,
            'payment_method': 'card',
        },
    )
    assert invoice_response.status_code == 201
    invoice = invoice_response.get_json()['data']
    assert invoice['status'] in ('issued', 'partially_paid')
    assert invoice['customer_id'] == customer.id
    assert invoice['items'][0]['quantity'] == 1

    payment_response = client.post(
        f"/api/v1/invoices/{invoice['id']}/payment",
        headers=headers,
        json={'amount': float(invoice['balance_due']), 'method': 'card'},
    )
    assert payment_response.status_code == 200
    payment = payment_response.get_json()['data']
    assert payment['invoice_id'] == invoice['id']
    assert payment['amount'] == float(invoice['balance_due'])

    return_response = client.post(
        '/api/v1/returns',
        headers=headers,
        json={
            'return_type': 'customer',
            'product_id': product.id,
            'quantity': 1,
            'customer_id': customer.id,
            'refund_amount': 5.0,
            'restock': True,
            'reason': 'Defective item',
        },
    )
    assert return_response.status_code == 201
    return_order = return_response.get_json()['data']
    assert return_order['return_type'] == 'customer'
    assert return_order['status'] == 'pending'

    approve_response = client.post(f"/api/v1/returns/{return_order['id']}/approve", headers=headers)
    assert approve_response.status_code == 200
    approved = approve_response.get_json()['data']
    assert approved['status'] in ('processed', 'refunded')
