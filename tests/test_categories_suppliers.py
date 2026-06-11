from app.models import Category, Supplier


def test_category_add_edit_delete_flow(admin_client, database):
    rv = admin_client.post(
        '/categories/add',
        data={'name': 'Office Supplies', 'description': 'Office items'},
        follow_redirects=True,
    )
    assert rv.status_code == 200
    assert b'Category saved successfully' in rv.data
    category = Category.query.filter_by(name='Office Supplies').first()
    assert category is not None

    rv = admin_client.post(
        f'/categories/{category.id}/edit',
        data={'name': 'Office Supplies Updated', 'description': 'Updated description'},
        follow_redirects=True,
    )
    assert rv.status_code == 200
    assert b'Category updated successfully' in rv.data
    assert Category.query.get(category.id).name == 'Office Supplies Updated'

    rv = admin_client.post(f'/categories/{category.id}/delete', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Category deleted successfully' in rv.data
    assert Category.query.get(category.id) is None


def test_supplier_add_edit_delete_flow(admin_client, database):
    rv = admin_client.post(
        '/suppliers/add',
        data={'name': 'Test Supplier', 'email': 'supplier@example.com', 'phone': '555-2222', 'address': '123 Test Lane'},
        follow_redirects=True,
    )
    assert rv.status_code == 200
    assert b'Supplier saved successfully' in rv.data
    supplier = Supplier.query.filter_by(name='Test Supplier').first()
    assert supplier is not None

    rv = admin_client.post(
        f'/suppliers/{supplier.id}/edit',
        data={'name': 'Test Supplier Updated', 'email': 'supplier@example.com', 'phone': '555-2222', 'address': '123 Test Lane'},
        follow_redirects=True,
    )
    assert rv.status_code == 200
    assert b'Supplier updated successfully' in rv.data
    assert Supplier.query.get(supplier.id).name == 'Test Supplier Updated'

    rv = admin_client.post(f'/suppliers/{supplier.id}/delete', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Supplier deleted successfully' in rv.data
    assert Supplier.query.get(supplier.id) is None
