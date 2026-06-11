import json


def test_api_docs_and_openapi_spec(api_client):
    response = api_client.get('/api/docs')
    assert response.status_code == 200
    assert 'openapi.json' in response.get_data(as_text=True)

    response = api_client.get('/api/redoc')
    assert response.status_code == 200
    assert 'openapi.json' in response.get_data(as_text=True)

    response = api_client.get('/api/openapi.json')
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert '/api/v1/warehouses' in payload['paths']
    assert '/api/v1/suppliers' in payload['paths']
    assert '/api/v1/warehouses/{warehouse_id}/inventory' in payload['paths']
    assert '/api/v1/suppliers/{supplier_id}/products' in payload['paths']
    assert '/api/v1/purchase-orders' in payload['paths']
    assert '/api/v1/purchase-orders/{purchase_order_id}/approve' in payload['paths']
    assert '/api/v1/purchase-orders/{purchase_order_id}/receive' in payload['paths']
    assert '/api/v1/purchase-orders/{purchase_order_id}/cancel' in payload['paths']
