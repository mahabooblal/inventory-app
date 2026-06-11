from app.models import ActivityLog, Product


def test_activity_log_created_for_product_creation(manager_client, category, supplier):
    response = manager_client.post(
        '/products/add',
        data={
            'name': 'Recordable Gadget',
            'sku': 'LOG123',
            'barcode': '123456789',
            'description': 'Track activity',
            'price': '15.00',
            'cost_price': '8.00',
            'quantity': '5',
            'low_stock_limit': '2',
            'category_id': str(category.id),
            'supplier_id': str(supplier.id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    product = Product.query.filter_by(sku='LOG123').first()
    log = ActivityLog.query.filter_by(entity_type='Product', entity_id=product.id, action='CREATE').first()
    assert log is not None
    assert 'Added product' in log.description


def test_activity_log_updated_for_product_edit(manager_client, category, supplier):
    response = manager_client.post(
        '/products/add',
        data={
            'name': 'Edit Gadget',
            'sku': 'EDIT123',
            'barcode': '123456789',
            'description': 'Initial product',
            'price': '20.00',
            'cost_price': '10.00',
            'quantity': '5',
            'low_stock_limit': '2',
            'category_id': str(category.id),
            'supplier_id': str(supplier.id),
        },
        follow_redirects=True,
    )

    product = Product.query.filter_by(sku='EDIT123').first()
    response = manager_client.post(
        f'/products/{product.id}/edit',
        data={
            'name': 'Edit Gadget Pro',
            'sku': 'EDIT123',
            'barcode': '123456789',
            'description': 'Updated product',
            'price': '22.00',
            'cost_price': '11.00',
            'quantity': '6',
            'low_stock_limit': '2',
            'category_id': str(category.id),
            'supplier_id': str(supplier.id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    log = ActivityLog.query.filter_by(entity_type='Product', entity_id=product.id, action='UPDATE').first()
    assert log is not None
    assert 'Updated product' in log.description
