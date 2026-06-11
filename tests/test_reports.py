from datetime import date


def test_reports_page_loads(manager_client):
    response = manager_client.get('/reports/')
    assert response.status_code == 200
    assert b'Reports' in response.data


def test_low_stock_report_view(manager_client):
    response = manager_client.post(
        '/reports/',
        data={
            'report_type': 'low_stock',
            'from_date': '2000-01-01',
            'to_date': '2100-01-01',
            'product_id': '0',
            'category_id': '0',
            'customer_id': '0',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'Reports' in response.data


def test_inventory_report_view(manager_client):
    response = manager_client.post(
        '/reports/',
        data={
            'report_type': 'inventory',
            'from_date': '2000-01-01',
            'to_date': '2100-01-01',
            'product_id': '0',
            'category_id': '0',
            'customer_id': '0',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'Reports' in response.data


def test_profit_loss_report_view(manager_client):
    response = manager_client.post(
        '/reports/',
        data={
            'report_type': 'profit_loss',
            'from_date': '2000-01-01',
            'to_date': '2100-01-01',
            'product_id': '0',
            'category_id': '0',
            'customer_id': '0',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'Reports' in response.data


def test_sales_csv_export(manager_client):
    response = manager_client.get(
        '/reports/export/sales/csv?from_date=2000-01-01&to_date=2100-01-01',
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert 'text/csv' in response.headers.get('Content-Type', '')
    assert 'attachment; filename=sales_report.csv' in response.headers.get('Content-Disposition', '')


def test_sales_pdf_export(manager_client):
    response = manager_client.get(
        '/reports/export/sales/pdf?from_date=2000-01-01&to_date=2100-01-01',
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert 'application/pdf' in response.headers.get('Content-Type', '')


def test_report_filter_sales(manager_client, category, supplier, product):
    response = manager_client.post(
        '/reports/',
        data={
            'report_type': 'sales',
            'from_date': '2000-01-01',
            'to_date': '2100-01-01',
            'product_id': '0',
            'category_id': '0',
            'customer_id': '0',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Reports' in response.data
