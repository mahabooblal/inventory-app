from datetime import datetime, time
from decimal import Decimal

from app import db
from app.models import Product, PurchaseOrder, PurchaseOrderItem
from app.services.activity_service import log_operation_timeline
from app.services.inventory_service import add_stock
from app.utils.datetime import utc_now


def next_po_number():
    next_id = (db.session.query(db.func.max(PurchaseOrder.id)).scalar() or 0) + 1
    return f'PO-{utc_now().strftime("%Y%m%d")}-{next_id:05d}'


def create_purchase_order(supplier_id, items, user_id, *, expected_date=None, notes=None):
    clean_items = []
    for item in items:
        product_id = int(item.get('product_id') or 0)
        quantity = int(item.get('quantity_ordered') or 0)
        unit_cost = Decimal(str(item.get('unit_cost') or 0))
        if product_id and quantity > 0:
            clean_items.append((product_id, quantity, unit_cost))
    if not clean_items:
        raise ValueError('Add at least one purchase order item.')

    purchase_order = PurchaseOrder(
        po_number=next_po_number(),
        supplier_id=supplier_id,
        status='draft',
        expected_date=expected_date,
        notes=notes,
        created_by=user_id,
    )
    db.session.add(purchase_order)
    db.session.flush()
    for product_id, quantity, unit_cost in clean_items:
        product = db.session.get(Product, product_id)
        if product is None:
            raise ValueError('Product not found')
        db.session.add(PurchaseOrderItem(
            purchase_order_id=purchase_order.id,
            product_id=product_id,
            quantity_ordered=quantity,
            unit_cost=unit_cost,
        ))
    db.session.flush()
    log_operation_timeline(
        user_id,
        'PurchaseOrder',
        purchase_order.id,
        'created',
        comment=f'Created purchase order {purchase_order.po_number}',
        extra={'status': purchase_order.status},
    )
    return purchase_order


def submit_purchase_order(purchase_order_id, user_id):
    purchase_order = db.session.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        raise ValueError('Purchase order not found')
    if purchase_order.status not in {'draft'}:
        raise ValueError('Only draft purchase orders can be submitted for approval.')
    purchase_order.status = 'pending'
    purchase_order.approved_by = None
    purchase_order.approved_at = None
    log_operation_timeline(
        user_id,
        'PurchaseOrder',
        purchase_order.id,
        'submitted',
        comment=f'Submitted purchase order {purchase_order.po_number} for approval',
        extra={'status': purchase_order.status},
    )
    return purchase_order


def approve_purchase_order(purchase_order_id, approver_id):
    purchase_order = db.session.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        raise ValueError('Purchase order not found')
    if purchase_order.status != 'pending':
        raise ValueError('Only pending purchase orders can be approved.')
    purchase_order.status = 'ordered'
    purchase_order.approved_by = approver_id
    purchase_order.approved_at = utc_now()
    purchase_order.ordered_at = utc_now()
    log_operation_timeline(
        approver_id,
        'PurchaseOrder',
        purchase_order.id,
        'approved',
        comment=f'Approved purchase order {purchase_order.po_number}',
        extra={'status': purchase_order.status},
    )
    return purchase_order


def reject_purchase_order(purchase_order_id, approver_id, reason=None):
    purchase_order = db.session.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        raise ValueError('Purchase order not found')
    if purchase_order.status != 'pending':
        raise ValueError('Only pending purchase orders can be rejected.')
    purchase_order.status = 'rejected'
    purchase_order.rejection_reason = reason
    purchase_order.approved_by = approver_id
    purchase_order.approved_at = utc_now()
    log_operation_timeline(
        approver_id,
        'PurchaseOrder',
        purchase_order.id,
        'rejected',
        comment=reason or f'Rejected purchase order {purchase_order.po_number}',
        extra={'status': purchase_order.status},
    )
    return purchase_order


def cancel_purchase_order(purchase_order_id, user_id, reason=None):
    purchase_order = db.session.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        raise ValueError('Purchase order not found')
    if purchase_order.status not in {'draft', 'pending'}:
        raise ValueError('Only draft or pending purchase orders can be cancelled.')
    purchase_order.status = 'cancelled'
    purchase_order.cancellation_reason = reason
    purchase_order.approved_by = user_id
    purchase_order.approved_at = utc_now()
    log_operation_timeline(
        user_id,
        'PurchaseOrder',
        purchase_order.id,
        'cancelled',
        comment=reason or f'Cancelled purchase order {purchase_order.po_number}',
        extra={'status': purchase_order.status},
    )
    return purchase_order


def receive_purchase_order(purchase_order_id, received_quantities, user_id, *, batch_reference=None, expires_on=None):
    purchase_order = db.session.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        raise ValueError('Purchase order not found')
    if purchase_order.status in {'received', 'cancelled'}:
        raise ValueError('This purchase order cannot receive more stock.')

    total_received_now = 0
    for item in purchase_order.items:
        receive_qty = int(received_quantities.get(str(item.id)) or 0)
        if receive_qty <= 0:
            continue
        if receive_qty > item.remaining_quantity:
            raise ValueError(f'Receive quantity for {item.product.name} exceeds remaining PO quantity.')
        item.quantity_received += receive_qty
        total_received_now += receive_qty
        add_stock(
            item.product_id,
            purchase_order.supplier_id,
            receive_qty,
            f'Received against {purchase_order.po_number}',
            user_id,
            batch_reference=batch_reference or item.batch_reference or purchase_order.po_number,
            expires_on=expires_on or item.expires_on,
            receive_date=datetime.combine(utc_now().date(), time.min),
            unit_cost=item.unit_cost,
            reference_type='PurchaseOrder',
            reference_id=purchase_order.id,
            commit=False,
        )

    if total_received_now <= 0:
        raise ValueError('Enter at least one quantity to receive.')

    if all(item.remaining_quantity == 0 for item in purchase_order.items):
        purchase_order.status = 'received'
    else:
        purchase_order.status = 'partially_received'
    log_operation_timeline(
        user_id,
        'PurchaseOrder',
        purchase_order.id,
        'stock_received',
        comment=f'Received stock against {purchase_order.po_number}',
        extra={
            'status': purchase_order.status,
            'received_quantity': total_received_now,
        },
    )
    return purchase_order
