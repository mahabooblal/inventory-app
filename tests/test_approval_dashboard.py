from app import db
from app.models import StockAdjustment, StockTransfer, ReturnOrder, PurchaseOrder
from app.services.stock_adjustment_service import request_stock_adjustment
from app.services.purchase_order_service import create_purchase_order, submit_purchase_order
from app.services.return_service import request_return
from app.services.warehouse_service import (
    create_warehouse,
    get_or_create_default_warehouse,
    warehouse_balance,
    request_stock_transfer,
)


def test_admin_approval_dashboard_lists_pending_requests(admin_client, manager_user, product, supplier, customer):
    source_warehouse = get_or_create_default_warehouse()
    destination_warehouse = create_warehouse('Secondary Warehouse', 'SEC', 'Secondary location')

    adjustment = request_stock_adjustment(product.id, 'found', 3, 'Test adjustment', manager_user.id)
    transfer = request_stock_transfer(product.id, source_warehouse.id, destination_warehouse.id, 1, manager_user.id, note='Pending transfer')
    purchase_order = create_purchase_order(
        supplier.id,
        [{'product_id': product.id, 'quantity_ordered': 2, 'unit_cost': 8.50}],
        manager_user.id,
    )
    submit_purchase_order(purchase_order.id, manager_user.id)
    return_order = request_return(
        'customer',
        product.id,
        1,
        manager_user.id,
        customer_id=customer.id,
        restock=False,
        reason='Test return',
    )
    db.session.commit()

    response = admin_client.get('/dashboard/approvals')

    assert response.status_code == 200
    assert b'Pending Stock Adjustments' in response.data
    assert str(adjustment.id).encode() in response.data
    assert b'Pending Warehouse Transfers' in response.data
    assert str(transfer.id).encode() in response.data
    assert b'Pending Purchase Orders' in response.data
    assert str(purchase_order.id).encode() in response.data
    assert b'Pending Return Requests' in response.data
    assert str(return_order.id).encode() in response.data


def test_admin_can_approve_transfer_and_return_requests(admin_client, manager_user, product, customer):
    source_warehouse = get_or_create_default_warehouse()
    destination_warehouse = create_warehouse('Secondary Warehouse', 'SEC', 'Secondary location')

    source_balance = warehouse_balance(source_warehouse.id, product.id)
    source_balance.quantity = 5
    db.session.commit()

    transfer = request_stock_transfer(product.id, source_warehouse.id, destination_warehouse.id, 3, manager_user.id)
    db.session.commit()
    approve_transfer_response = admin_client.post(
        f'/warehouses/transfers/{transfer.id}/approve',
        data={'csrf_token': 'test'},
        follow_redirects=True,
    )
    assert approve_transfer_response.status_code == 200

    db.session.refresh(transfer)
    assert transfer.status == 'completed'
    destination_balance = warehouse_balance(destination_warehouse.id, product.id)
    assert destination_balance.quantity == 3

    return_order = request_return(
        'customer',
        product.id,
        2,
        manager_user.id,
        customer_id=customer.id,
        restock=True,
        reason='Customer return',
    )
    db.session.commit()

    approve_return_response = admin_client.post(
        f'/returns/{return_order.id}/approve',
        data={'csrf_token': 'test'},
        follow_redirects=True,
    )
    assert approve_return_response.status_code == 200

    db.session.refresh(return_order)
    assert return_order.status == 'processed'
    db.session.refresh(product)
    assert product.quantity == 7
