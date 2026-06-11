from app import db
from app.models import Product, StockAdjustment
from app.services.activity_service import log_operation_timeline
from app.services.inventory_service import create_stock_movement
from app.utils.datetime import utc_now


def request_stock_adjustment(product_id, adjustment_type, quantity_delta, reason, user_id):
    if int(quantity_delta) == 0:
        raise ValueError('Adjustment quantity cannot be zero.')
    product = db.session.get(Product, product_id)
    if product is None:
        raise ValueError('Product not found')
    adjustment = StockAdjustment(
        product_id=product_id,
        adjustment_type=adjustment_type,
        quantity_delta=int(quantity_delta),
        reason=reason,
        requested_by=user_id,
    )
    db.session.add(adjustment)
    db.session.flush()
    log_operation_timeline(
        user_id,
        'StockAdjustment',
        adjustment.id,
        'created',
        comment=f'Requested stock adjustment for {adjustment.product.name}',
        extra={'status': adjustment.status},
    )
    return adjustment


def approve_stock_adjustment(adjustment_id, approver_id):
    adjustment = db.session.get(StockAdjustment, adjustment_id)
    if adjustment is None:
        raise ValueError('Stock adjustment not found')
    if adjustment.status != 'pending':
        raise ValueError('Only pending adjustments can be approved.')

    product = adjustment.product
    quantity_before = product.quantity
    quantity_after = quantity_before + adjustment.quantity_delta
    if quantity_after < 0:
        raise ValueError('Approved adjustment would make stock negative.')

    product.quantity = quantity_after
    adjustment.status = 'approved'
    adjustment.approved_by = approver_id
    adjustment.approved_at = utc_now()
    log_operation_timeline(
        approver_id,
        'StockAdjustment',
        adjustment.id,
        'approved',
        comment=f'Approved adjustment for {adjustment.product.name}',
        extra={'status': adjustment.status},
    )
    db.session.add(create_stock_movement(
        product,
        'adjustment',
        adjustment.quantity_delta,
        approver_id,
        reference_type='StockAdjustment',
        reference_id=adjustment.id,
        note=adjustment.reason,
        quantity_before=quantity_before,
    ))
    return adjustment


def reject_stock_adjustment(adjustment_id, approver_id, reason=None):
    adjustment = db.session.get(StockAdjustment, adjustment_id)
    if adjustment is None:
        raise ValueError('Stock adjustment not found')
    if adjustment.status != 'pending':
        raise ValueError('Only pending adjustments can be rejected.')
    adjustment.status = 'rejected'
    adjustment.rejection_reason = reason
    adjustment.approved_by = approver_id
    adjustment.approved_at = utc_now()
    log_operation_timeline(
        approver_id,
        'StockAdjustment',
        adjustment.id,
        'rejected',
        comment=reason or f'Rejected stock adjustment for {adjustment.product.name}',
        extra={'status': adjustment.status},
    )
    return adjustment


def cancel_stock_adjustment(adjustment_id, user_id, reason=None):
    adjustment = db.session.get(StockAdjustment, adjustment_id)
    if adjustment is None:
        raise ValueError('Stock adjustment not found')
    if adjustment.status != 'pending':
        raise ValueError('Only pending adjustments can be cancelled.')
    adjustment.status = 'cancelled'
    adjustment.cancellation_reason = reason
    adjustment.approved_by = user_id
    adjustment.approved_at = utc_now()
    log_operation_timeline(
        user_id,
        'StockAdjustment',
        adjustment.id,
        'cancelled',
        comment=reason or f'Cancelled stock adjustment request for {adjustment.product.name}',
        extra={'status': adjustment.status},
    )
    return adjustment
