from app.models import Product, Sale, StockIn


def test_product_creation_by_manager(manager_client, category, supplier):
    response = manager_client.post(
        '/products/add',
        data={
            'name': 'Gadget X',
            'sku': 'G123',
            'barcode': '123456789',
            'description': 'Updated gadget',
            'price': '12.50',
            'cost_price': '6.00',
            'quantity': '10',
            'low_stock_limit': '3',
            'category_id': str(category.id),
            'supplier_id': str(supplier.id),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Product added successfully' in response.data
    assert Product.query.filter_by(sku='G123').first() is not None


def test_staff_cannot_add_product(staff_client, category, supplier):
    response = staff_client.post(
        '/products/add',
        data={
            'name': 'Unauthorized Gadget',
            'sku': 'G999',
            'barcode': '999999999',
            'description': 'Should be forbidden',
            'price': '10.00',
            'cost_price': '5.00',
            'quantity': '1',
            'low_stock_limit': '1',
            'category_id': str(category.id),
            'supplier_id': str(supplier.id),
        },
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_stock_increase(admin_client, product, supplier):
    response = admin_client.post(
        '/stock/in',
        data={
            'product_id': str(product.id),
            'supplier_id': str(supplier.id),
            'quantity': '10',
            'note': 'Receive shipment',
        },
        follow_redirects=True,
    )

    product = Product.query.get(product.id)
    assert response.status_code == 200
    assert b'Stock added and product quantity updated.' in response.data
    assert product.quantity == 15
    assert StockIn.query.filter_by(product_id=product.id).count() == 1


def test_insufficient_stock_prevention(admin_client, product):
    response = admin_client.post(
        '/sales/new',
        data={
            'product_id': str(product.id),
            'customer_id': '0',
            'quantity': '10',
            'selling_price': '15.00',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Sale quantity cannot be greater than available stock.' in response.data
    assert Product.query.get(product.id).quantity == 5
