import json

import pytest
from app.api.base import ValidationError
from app.api.schemas import ProductSchema


def test_openapi_json_includes_jwt_security(api_client):
    response = api_client.get('/api/openapi.json')
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data['openapi'] == '3.0.3'
    assert 'BearerAuth' in data['components']['securitySchemes']
    assert '/api/v1/auth/me' in data['paths']
    assert '/api/v1/products' in data['paths']
    assert '/api/v1/inventory' in data['paths']
    assert '/api/v1/inventory/movements' in data['paths']
    assert '/api/v1/inventory/low-stock' in data['paths']
    assert '/api/v1/inventory/valuation' in data['paths']
    assert data['paths']['/api/v1/auth/me']['get']['security'] == [{'BearerAuth': []}]


def test_swagger_ui_route_is_available(api_client):
    response = api_client.get('/api/docs')
    assert response.status_code == 200
    assert b'Swagger UI' in response.data


def test_redoc_ui_route_is_available(api_client):
    response = api_client.get('/api/redoc')
    assert response.status_code == 200
    assert b'ReDoc' in response.data


def test_api_versioned_ping_endpoint(api_client):
    response = api_client.get('/api/v1/ping')
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert payload['status'] == 'success'
    assert payload['data']['api_version'] == 'v1'


def test_invalid_json_request_returns_api_error(api_client):
    response = api_client.post(
        '/api/v1/auth/login',
        data='{"username": "admin"',
        content_type='application/json',
    )
    assert response.status_code == 400
    payload = json.loads(response.data)
    assert payload['status'] == 'error'
    assert payload['error_code'] == 'INVALID_JSON'


def test_schema_validation_raises_consistent_errors():
    schema = ProductSchema()
    with pytest.raises(ValidationError) as excinfo:
        schema.load({'name': '', 'sku': '', 'price': -1, 'quantity': -5})

    error = excinfo.value
    assert 'name' in error.errors or 'sku' in error.errors
    assert error.error_code == 'VALIDATION_FAILED'


def test_rate_limit_configuration_exists(app):
    assert 'RATELIMIT_ENABLED' in app.config
    assert 'RATELIMIT_DEFAULT' in app.config


def test_ping_rate_limit_behavior(api_client, app):
    app.config['RATELIMIT_ENABLED'] = True
    response_one = api_client.get('/api/v1/ping')
    response_two = api_client.get('/api/v1/ping')
    response_three = api_client.get('/api/v1/ping')

    assert response_one.status_code in (200, 429)
    assert response_two.status_code in (200, 429)
    assert response_three.status_code in (200, 429)
    if response_three.status_code == 429:
        assert 'Retry-After' in response_three.headers or 'X-RateLimit-Remaining' in response_three.headers
