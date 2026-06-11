from datetime import date, timedelta

from app import db
from app.models import Product, ReturnOrder, StockMovement, StockTransfer, Warehouse, WarehouseStock
from app.services.warehouse_service import warehouse_balance


def test_warehouse_transfer_moves_location_balance(manager_client, product):
    main = Warehouse(name='Main Branch', code='MAIN1')
    outlet = Warehouse(name='Outlet Branch', code='OUT1')
    db.session.add_all([main, outlet])
    db.session.flush()
    warehouse_balance(main.id, product.id).quantity = 5
    db.session.add(WarehouseStock(warehouse_id=outlet.id, product_id=product.id, quantity=0))
    db.session.commit()

    response = manager_client.post(
        '/warehouses/transfers',
        data={
            'product_id': str(product.id),
            'source_warehouse_id': str(main.id),
            'destination_warehouse_id': str(outlet.id),
            'quantity': '2',
            'note': 'Move to outlet',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Stock transfer request submitted for approval.' in response.data
    
    # Get the transfer and approve it
    transfer = StockTransfer.query.first()
    assert transfer is not None
    response = manager_client.post(
        f'/warehouses/transfers/{transfer.id}/approve',
        follow_redirects=True,
    )
    assert response.status_code == 200
    
    assert WarehouseStock.query.filter_by(warehouse_id=main.id, product_id=product.id).first().quantity == 3
    assert WarehouseStock.query.filter_by(warehouse_id=outlet.id, product_id=product.id).first().quantity == 2
    assert StockMovement.query.filter_by(reference_type='StockTransfer').count() == 1


def test_customer_return_restocks_and_records_refund(admin_client, product, customer):
    response = admin_client.post(
        '/returns/',
        data={
            'return_type': 'customer',
            'product_id': str(product.id),
            'customer_id': str(customer.id),
            'supplier_id': '0',
            'quantity': '2',
            'refund_amount': '15.00',
            'restock': 'y',
            'reason': 'Customer returned sealed product',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Return request submitted for approval.' in response.data
    
    # Get the return order and approve it
    return_order = ReturnOrder.query.first()
    assert return_order is not None
    response = admin_client.post(
        f'/returns/{return_order.id}/approve',
        follow_redirects=True,
    )
    assert response.status_code == 200
    
    return_order = ReturnOrder.query.get(return_order.id)
    assert Product.query.get(product.id).quantity == 7
    assert return_order.status == 'refunded'
    movement = StockMovement.query.filter_by(reference_type='ReturnOrder', reference_id=return_order.id).first()
    assert movement.quantity == 2
    assert movement.quantity_before == 5
    assert movement.quantity_after == 7


def test_supplier_return_reduces_stock(admin_client, product, supplier):
    response = admin_client.post(
        '/returns/',
        data={
            'return_type': 'supplier',
            'product_id': str(product.id),
            'customer_id': '0',
            'supplier_id': str(supplier.id),
            'quantity': '1',
            'refund_amount': '5.00',
            'reason': 'Defective from supplier',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    
    # Get the return order and approve it
    return_order = ReturnOrder.query.first()
    assert return_order is not None
    response = admin_client.post(
        f'/returns/{return_order.id}/approve',
        follow_redirects=True,
    )
    assert response.status_code == 200
    
    assert Product.query.get(product.id).quantity == 4


def test_operations_pages_load(manager_client, product, supplier):
    manager_client.post(
        '/stock/in',
        data={
            'product_id': str(product.id),
            'supplier_id': str(supplier.id),
            'batch_reference': 'EXP-1',
            'expires_on': (date.today() + timedelta(days=10)).isoformat(),
            'receive_date': date.today().isoformat(),
            'quantity': '1',
            'unit_cost': '5.00',
            'note': 'Expiry test',
        },
        follow_redirects=True,
    )

    for path in ['/operations/reorder', '/operations/analytics', '/operations/expiry', '/operations/reconciliation']:
        response = manager_client.get(path)
        assert response.status_code == 200


def test_reconciliation_page_shows_mismatched_products(manager_client, product):
    response = manager_client.get('/operations/reconciliation')
    assert response.status_code == 200
    assert b'G123' in response.data
    assert b'Reconciliation Dashboard' in response.data


def test_reconciliation_bootstrap_creates_warehouse_stock(manager_client, product):
    main = Warehouse(name='Main Branch', code='MAIN')
    db.session.add(main)
    db.session.commit()

    response = manager_client.post('/operations/reconciliation/bootstrap', follow_redirects=True)
    assert response.status_code == 200
    assert b'Bootstrapped 1 missing warehouse balances.' in response.data
    balance = WarehouseStock.query.filter_by(product_id=product.id, warehouse_id=main.id).first()
    assert balance is not None
    assert balance.quantity == 5


def test_activity_log_filters(admin_client, product, supplier):
    admin_client.post(
        '/products/add',
        data={
            'name': 'Audit Item',
            'sku': 'AUD123',
            'barcode': 'AUD123',
            'description': 'Audit',
            'price': '10.00',
            'cost_price': '5.00',
            'quantity': '1',
            'low_stock_limit': '1',
            'category_id': str(product.category_id),
            'supplier_id': str(supplier.id),
        },
        follow_redirects=True,
    )
    response = admin_client.get('/activity-logs/?action=CREATE&entity_type=Product')
    assert response.status_code == 200
    assert b'Audit Item' in response.data
