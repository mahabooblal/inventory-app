from decimal import Decimal

from app import db
from app.models import Product, ReturnOrder
from app.services.activity_service import log_operation_timeline
from app.services.inventory_service import create_stock_movement
from app.utils.datetime import utc_now


def next_return_number():
    next_id = (db.session.query(db.func.max(ReturnOrder.id)).scalar() or 0) + 1
    return f'RMA-{utc_now().strftime("%Y%m%d")}-{next_id:05d}'


def _apply_return(return_order, user_id):
    product = db.session.get(Product, return_order.product_id)
    if product is None:
        raise ValueError('Product not found')
    quantity_before = product.quantity
    movement_qty = 0
    if return_order.return_type == 'customer' and return_order.restock:
        product.quantity += return_order.quantity
        movement_qty = return_order.quantity
    elif return_order.return_type == 'supplier':
        if return_order.quantity > product.quantity:
            raise ValueError('Supplier return quantity cannot exceed available stock.')
        product.quantity -= return_order.quantity
        movement_qty = -return_order.quantity

    if return_order.refund_amount > 0:
        return_order.status = 'refunded'
    else:
        return_order.status = 'processed'
    return_order.approved_by = user_id
    return_order.approved_at = utc_now()

    db.session.add(create_stock_movement(
        product,
        'return',
        movement_qty,
        user_id,
        reference_type='ReturnOrder',
        reference_id=return_order.id,
        note=return_order.reason,
        quantity_before=quantity_before,
    ))
    return return_order


def request_return(return_type, product_id, quantity, user_id, *, customer_id=None, supplier_id=None, refund_amount=0, restock=True, reason=''):
    product = db.session.get(Product, product_id)
    if product is None:
        raise ValueError('Product not found')
    if quantity <= 0:
        raise ValueError('Return quantity must be positive.')

    return_order = ReturnOrder(
        return_number=next_return_number(),
        return_type=return_type,
        product_id=product_id,
        customer_id=customer_id if return_type == 'customer' else None,
        supplier_id=supplier_id if return_type == 'supplier' else None,
        quantity=quantity,
        refund_amount=Decimal(str(refund_amount or 0)),
        restock=restock,
        reason=reason,
        status='pending',
        created_by=user_id,
    )
    db.session.add(return_order)
    db.session.flush()
    log_operation_timeline(
        user_id,
        'ReturnOrder',
        return_order.id,
        'created',
        comment=f'Requested return {return_order.return_number}',
        extra={'status': return_order.status},
    )
    return return_order


def approve_return(return_order_id, approver_id):
    return_order = db.session.get(ReturnOrder, return_order_id)
    if return_order is None:
        raise ValueError('Return order not found')
    if return_order.status != 'pending':
        raise ValueError('Only pending returns can be approved.')
    approved = _apply_return(return_order, approver_id)
    log_operation_timeline(
        approver_id,
        'ReturnOrder',
        return_order.id,
        'approved',
        comment=f'Approved return {return_order.return_number}',
        extra={'status': return_order.status},
    )
    return approved


def reject_return(return_order_id, approver_id, reason=None):
    return_order = db.session.get(ReturnOrder, return_order_id)
    if return_order is None:
        raise ValueError('Return order not found')
    if return_order.status != 'pending':
        raise ValueError('Only pending returns can be rejected.')
    return_order.status = 'rejected'
    return_order.rejection_reason = reason
    return_order.approved_by = approver_id
    return_order.approved_at = utc_now()
    log_operation_timeline(
        approver_id,
        'ReturnOrder',
        return_order.id,
        'rejected',
        comment=reason or f'Rejected return {return_order.return_number}',
        extra={'status': return_order.status},
    )
    return return_order


def cancel_return(return_order_id, user_id, reason=None):
    return_order = db.session.get(ReturnOrder, return_order_id)
    if return_order is None:
        raise ValueError('Return order not found')
    if return_order.status != 'pending':
        raise ValueError('Only pending returns can be cancelled.')
    return_order.status = 'cancelled'
    return_order.cancellation_reason = reason
    return_order.approved_by = user_id
    return_order.approved_at = utc_now()
    log_operation_timeline(
        user_id,
        'ReturnOrder',
        return_order.id,
        'cancelled',
        comment=reason or f'Cancelled return {return_order.return_number}',
        extra={'status': return_order.status},
    )
    return return_order
