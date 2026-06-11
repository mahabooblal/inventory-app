def test_reports_invalid_filters(manager_client):
    rv = manager_client.get('/reports/export/sales/csv?from_date=bad&to_date=also', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Invalid report filter values.' in rv.data

def test_reports_profit_pdf_empty(manager_client):
    rv = manager_client.get('/reports/export/profit_loss/pdf', follow_redirects=False)
    assert rv.status_code == 200
    assert 'application/pdf' in rv.headers.get('Content-Type', '')
