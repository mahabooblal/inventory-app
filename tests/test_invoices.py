from decimal import Decimal

from app.models import Invoice, Product, StockMovement


def test_multi_line_invoice_deducts_stock_and_tracks_payment(admin_client, product, customer, database, category, supplier):
    second = Product(
        name='Widget',
        sku='W123',
        price=20,
        cost_price=8,
        quantity=10,
        low_stock_limit=2,
        category_id=category.id,
        supplier_id=supplier.id,
    )
    database.session.add(second)
    database.session.commit()

    response = admin_client.post(
        '/invoices/new',
        data={
            'customer_id': str(customer.id),
            'notes': 'Counter sale',
            'payment_amount': '20.00',
            'payment_method': 'cash',
            'product_id': [str(product.id), str(second.id)],
            'quantity': ['2', '1'],
            'unit_price': ['10.00', '20.00'],
            'discount_amount': ['2.00', '0.00'],
            'tax_rate': ['18.00', '5.00'],
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Invoice created and stock deducted.' in response.data
    invoice = Invoice.query.first()
    assert invoice is not None
    assert invoice.subtotal == Decimal('40.00')
    assert invoice.discount_amount == Decimal('2.00')
    assert invoice.tax_amount == Decimal('4.24')
    assert invoice.total_amount == Decimal('42.24')
    assert invoice.amount_paid == Decimal('20.00')
    assert invoice.status == 'partially_paid'
    assert Product.query.get(product.id).quantity == 3
    assert Product.query.get(second.id).quantity == 9

    movements = StockMovement.query.filter_by(reference_type='Invoice', reference_id=invoice.id).all()
    assert len(movements) == 2
    assert {movement.quantity for movement in movements} == {-2, -1}


def test_invoice_prevents_overselling(admin_client, product):
    response = admin_client.post(
        '/invoices/new',
        data={
            'customer_id': '0',
            'notes': '',
            'payment_amount': '0',
            'payment_method': 'cash',
            'product_id': [str(product.id)],
            'quantity': ['99'],
            'unit_price': ['10.00'],
            'discount_amount': ['0.00'],
            'tax_rate': ['18.00'],
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Insufficient stock' in response.data
    assert Invoice.query.count() == 0
    assert Product.query.get(product.id).quantity == 5


def test_invoice_payment_and_pdf(admin_client, product):
    admin_client.post(
        '/invoices/new',
        data={
            'customer_id': '0',
            'notes': '',
            'payment_amount': '0',
            'payment_method': 'cash',
            'product_id': [str(product.id)],
            'quantity': ['1'],
            'unit_price': ['10.00'],
            'discount_amount': ['0.00'],
            'tax_rate': ['0.00'],
        },
        follow_redirects=True,
    )
    invoice = Invoice.query.first()

    response = admin_client.post(
        f'/invoices/{invoice.id}',
        data={'amount': '10.00', 'method': 'upi', 'reference': 'UPI123'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Payment recorded.' in response.data
    assert invoice.amount_paid == Decimal('10.00')
    assert invoice.status == 'paid'

    response = admin_client.get(f'/invoices/{invoice.id}/pdf')
    assert response.status_code == 200
    assert 'application/pdf' in response.headers.get('Content-Type', '')
    assert b'%PDF' in response.data[:4]
