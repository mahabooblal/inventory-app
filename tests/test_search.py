def test_search_returns_results(manager_client, product):
    rv = manager_client.get('/search/?q=Gadget')
    assert rv.status_code == 200
    assert b'Gadget' in rv.data


def test_search_no_results(manager_client):
    rv = manager_client.get('/search/?q=NonExistentProduct')
    assert rv.status_code == 200
    # page should render with no crash
    assert rv.data is not None
