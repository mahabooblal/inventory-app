from app.models import Product, PurchaseOrder, StockAdjustment, StockMovement


def test_purchase_order_partial_and_final_receiving(manager_client, product, supplier):
    response = manager_client.post(
        '/purchase-orders/new',
        data={
            'supplier_id': str(supplier.id),
            'expected_date': '2026-06-01',
            'notes': 'Weekly procurement',
            'product_id': [str(product.id), ''],
            'quantity_ordered': ['10', '0'],
            'unit_cost': ['4.50', '0'],
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    purchase_order = PurchaseOrder.query.first()
    assert purchase_order is not None
    assert purchase_order.status == 'draft'
    
    # Submit and approve the purchase order
    response = manager_client.post(
        f'/purchase-orders/{purchase_order.id}/submit',
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert purchase_order.status == 'pending'
    
    response = manager_client.post(
        f'/purchase-orders/{purchase_order.id}/approve',
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert purchase_order.status == 'ordered'
    item = purchase_order.items[0]

    response = manager_client.post(
        f'/purchase-orders/{purchase_order.id}/receive',
        data={
            'batch_reference': 'BATCH-1',
            f'receive_qty_{item.id}': '4',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Purchase order stock received.' in response.data
    assert purchase_order.status == 'partially_received'
    assert item.quantity_received == 4
    assert Product.query.get(product.id).quantity == 9

    movement = StockMovement.query.filter_by(reference_type='PurchaseOrder', reference_id=purchase_order.id).first()
    assert movement.quantity_before == 5
    assert movement.quantity_after == 9
    assert movement.batch_reference == 'BATCH-1'

    response = manager_client.post(
        f'/purchase-orders/{purchase_order.id}/receive',
        data={
            'batch_reference': 'BATCH-1',
            f'receive_qty_{item.id}': '6',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert purchase_order.status == 'received'
    assert item.quantity_received == 10
    assert Product.query.get(product.id).quantity == 15


def test_purchase_order_prevents_over_receiving(manager_client, product, supplier):
    manager_client.post(
        '/purchase-orders/new',
        data={
            'supplier_id': str(supplier.id),
            'expected_date': '2026-06-01',
            'notes': '',
            'product_id': [str(product.id)],
            'quantity_ordered': ['3'],
            'unit_cost': ['5.00'],
        },
        follow_redirects=True,
    )
    purchase_order = PurchaseOrder.query.first()
    item = purchase_order.items[0]

    response = manager_client.post(
        f'/purchase-orders/{purchase_order.id}/receive',
        data={f'receive_qty_{item.id}': '4'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'exceeds remaining PO quantity' in response.data
    assert Product.query.get(product.id).quantity == 5


def test_stock_adjustment_approval_updates_stock_and_ledger(admin_client, product):
    response = admin_client.post(
        '/stock-adjustments/',
        data={
            'product_id': str(product.id),
            'adjustment_type': 'damage',
            'quantity_delta': '-2',
            'reason': 'Damaged during handling',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    adjustment = StockAdjustment.query.first()
    assert adjustment.status == 'pending'

    response = admin_client.post(
        f'/stock-adjustments/{adjustment.id}/approve',
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Stock adjustment approved and ledger updated.' in response.data
    assert Product.query.get(product.id).quantity == 3
    assert adjustment.status == 'approved'

    movement = StockMovement.query.filter_by(reference_type='StockAdjustment', reference_id=adjustment.id).first()
    assert movement is not None
    assert movement.quantity == -2
    assert movement.quantity_before == 5
    assert movement.quantity_after == 3
