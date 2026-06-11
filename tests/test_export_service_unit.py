from collections import namedtuple
from datetime import datetime

from app.services import export_service


def make_sale(product_name='Gadget', qty=2, price=10.0, total=20.0):
    Product = namedtuple('Product', ['name'])
    Sale = namedtuple('Sale', ['sale_date', 'product', 'quantity', 'selling_price', 'total_amount'])
    return Sale(sale_date=datetime(2026, 1, 1), product=Product(name=product_name), quantity=qty, selling_price=price, total_amount=total)


def test_sales_csv_response(app):
    with app.app_context():
        csv_data = export_service.sales_csv_response([make_sale()])
        assert 'text/csv' in csv_data.headers.get('Content-Type', '')
        assert 'sales_report.csv' in csv_data.headers.get('Content-Disposition', '')
        assert 'Gadget' in csv_data.get_data(as_text=True)


def test_sales_pdf_response(app):
    with app.app_context():
        pdf_data = export_service.sales_pdf_response([make_sale()], total=20.0)
        assert 'application/pdf' in pdf_data.headers.get('Content-Type', '')
        assert b'%PDF' in pdf_data.get_data()[:4]


def test_inventory_csv_response(app):
    rows = [{'name': 'Gadget', 'sku': 'G123', 'quantity': 5, 'price': 10.0, 'cost_price': 5.0, 'total_value': 50.0, 'total_cost': 25.0}]
    with app.app_context():
        csv_data = export_service.inventory_csv_response(rows)
        assert 'text/csv' in csv_data.headers.get('Content-Type', '')
        assert 'inventory_report.csv' in csv_data.headers.get('Content-Disposition', '')


def test_inventory_pdf_response(app):
    rows = [{'name': 'Gadget', 'sku': 'G123', 'quantity': 5, 'total_value': 50.0}]
    with app.app_context():
        pdf_data = export_service.inventory_pdf_response(rows, totals={'value': 50.0})
        assert 'application/pdf' in pdf_data.headers.get('Content-Type', '')
        assert b'%PDF' in pdf_data.get_data()[:4]


def test_profit_csv_response(app):
    summary = {'revenue': 100.0, 'cost': 50.0, 'profit': 50.0}
    with app.app_context():
        csv_data = export_service.profit_csv_response(summary)
        assert 'text/csv' in csv_data.headers.get('Content-Type', '')
        assert 'profit_loss.csv' in csv_data.headers.get('Content-Disposition', '')


def test_profit_pdf_response(app):
    summary = {'revenue': 100.0, 'cost': 50.0, 'profit': 50.0}
    with app.app_context():
        pdf_data = export_service.profit_pdf_response(summary)
        assert 'application/pdf' in pdf_data.headers.get('Content-Type', '')
        assert b'%PDF' in pdf_data.get_data()[:4]
