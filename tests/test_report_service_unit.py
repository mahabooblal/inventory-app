from datetime import date

from app.models import Product, Sale
from app.services import report_service


def test_sales_total_calculation():
    sale = Sale(product_id=1, customer_id=None, quantity=2, selling_price=15.0, total_amount=30.0, created_by=1, sale_date=date.today())
    assert report_service.sales_total([sale]) == 30.0


def test_profit_loss_with_no_sales(database):
    result = report_service.profit_loss_between(date.today(), date.today())
    assert result['revenue'] == 0
    assert result['cost'] == 0
    assert result['profit'] == 0


def test_low_stock_products(database):
    from app.models import Product, Supplier, Category

    category = Category(name='Low Stock', description='Low stock category')
    supplier = Supplier(name='Low Supplier', email='low@example.com', phone='555-1111', address='Low stock address')
    db_product = Product(
        name='Low Gadget',
        sku='LOW1',
        barcode='000111222',
        description='Low stock gadget',
        price=5.00,
        cost_price=2.50,
        quantity=1,
        low_stock_limit=5,
        category=category,
        supplier=supplier,
    )
    from app import db
    db.session.add_all([category, supplier, db_product])
    db.session.commit()

    result = report_service.low_stock_products()
    assert isinstance(result, list)
    assert any(p.id == db_product.id for p in result)


def test_product_sales_between(manager_client, product):
    response = manager_client.post(
        '/sales/new',
        data={
            'product_id': str(product.id),
            'customer_id': '0',
            'quantity': '1',
            'selling_price': '15.00',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    result = report_service.product_sales_between(product.id, date.today(), date.today())
    assert isinstance(result, list)
