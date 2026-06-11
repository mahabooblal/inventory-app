import os
import tempfile

import pytest
from app import create_app, db
from app.models import Category, Customer, Product, Supplier, User
from config import TestingConfig


class TestConfig(TestingConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-secret-key-0123456789abcdef1234'
    AUTO_CREATE_DATABASE = False
    ADMIN_PASSWORD = None
    RATELIMIT_ENABLED = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False},
    }


@pytest.fixture(scope='session')
def app(tmp_path_factory):
    db_dir = tmp_path_factory.mktemp('db')
    db_file = db_dir / 'test_inventory.db'
    config = type('LocalTestingConfig', (TestConfig,), {
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_file}',
    })

    app = create_app(config_class=config)

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

    try:
        os.remove(db_file)
    except OSError:
        pass


@pytest.fixture(scope='function')
def database(app):
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    yield db
    db.session.remove()
    db.drop_all()
    db.engine.dispose()
    ctx.pop()


@pytest.fixture
def client(app, database):
    return app.test_client()


@pytest.fixture
def api_client(app, database):
    return app.test_client()


def login_client(client, username, password):
    return client.post(
        '/auth/login',
        data={'username': username, 'password': password},
        follow_redirects=True,
    )


@pytest.fixture
def admin_user(database):
    user = User(username='admin', email='admin@example.com', role='admin')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def manager_user(database):
    user = User(username='manager', email='manager@example.com', role='manager')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def staff_user(database):
    user = User(username='staff', email='staff@example.com', role='staff')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_client(client, admin_user):
    login_client(client, admin_user.username, 'password')
    return client


@pytest.fixture
def manager_client(client, manager_user):
    login_client(client, manager_user.username, 'password')
    return client


@pytest.fixture
def staff_client(client, staff_user):
    login_client(client, staff_user.username, 'password')
    return client


@pytest.fixture
def category(database):
    category = Category(name='Electronics', description='Test category')
    db.session.add(category)
    db.session.commit()
    return category


@pytest.fixture
def supplier(database):
    supplier = Supplier(name='Acme Corp', email='acme@example.com', phone='555-1234', address='123 Main St')
    db.session.add(supplier)
    db.session.commit()
    return supplier


@pytest.fixture
def product(database, category, supplier):
    product = Product(
        name='Gadget',
        sku='G123',
        barcode='123456789',
        description='Test gadget',
        price=10.00,
        cost_price=5.00,
        quantity=5,
        low_stock_limit=2,
        category_id=category.id,
        supplier_id=supplier.id,
    )
    db.session.add(product)
    db.session.commit()
    return product


@pytest.fixture
def customer(database):
    customer = Customer(name='Customer A', email='cust@example.com', phone='555-0000', address='Test address')
    db.session.add(customer)
    db.session.commit()
    return customer
