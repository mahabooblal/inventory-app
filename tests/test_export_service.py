def test_export_inventory_csv(manager_client):
    rv = manager_client.get('/reports/export/inventory/csv', follow_redirects=False)
    assert rv.status_code == 200
    assert 'text/csv' in rv.headers.get('Content-Type', '')


def test_export_inventory_pdf(manager_client):
    rv = manager_client.get('/reports/export/inventory/pdf', follow_redirects=False)
    assert rv.status_code == 200
    assert 'application/pdf' in rv.headers.get('Content-Type', '')
