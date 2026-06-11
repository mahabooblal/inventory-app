import os
import pytest
from flask import Flask

def make_app_with_token(token=None):
    from app import create_app
    class TestConfig:
        TESTING = True
        SECRET_KEY = 'test'
        METRICS_AUTH_TOKEN = token or ''
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        WTF_CSRF_ENABLED = False
        AUTO_CREATE_DATABASE = True
    return create_app(config_class=TestConfig)

@pytest.fixture
def client():
    app = make_app_with_token()
    with app.test_client() as client:
        yield client

@pytest.fixture
def client_with_token():
    app = make_app_with_token(token='test-token')
    with app.test_client() as client:
        yield client

def test_metrics_unprotected(client):
    resp = client.get('/metrics')
    assert resp.status_code == 200
    assert b'inventory_app_request_count' in resp.data

def test_metrics_protected_no_token(client_with_token):
    resp = client_with_token.get('/metrics')
    assert resp.status_code == 401

def test_metrics_protected_bad_token(client_with_token):
    resp = client_with_token.get('/metrics', headers={'Authorization': 'Bearer wrong'})
    assert resp.status_code == 403

def test_metrics_protected_good_token(client_with_token):
    resp = client_with_token.get('/metrics', headers={'Authorization': 'Bearer test-token'})
    assert resp.status_code == 200
    assert b'inventory_app_request_count' in resp.data
