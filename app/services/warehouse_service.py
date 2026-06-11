from sqlalchemy import select

from app import db
from app.models import Product, StockTransfer, Warehouse, WarehouseStock
from app.services.activity_service import log_operation_timeline
from app.services.inventory_service import create_stock_movement
from app.utils.datetime import utc_now


def next_transfer_number():
    next_id = (db.session.query(db.func.max(StockTransfer.id)).scalar() or 0) + 1
    return f'TRF-{utc_now().strftime("%Y%m%d")}-{next_id:05d}'


def get_or_create_default_warehouse():
    warehouse = Warehouse.query.order_by(Warehouse.id).first()
    if warehouse:
        return warehouse
    warehouse = Warehouse(name='Main Warehouse', code='MAIN', address='Default stock location')
    db.session.add(warehouse)
    db.session.flush()
    return warehouse


def warehouse_balance(warehouse_id, product_id):
    balance = WarehouseStock.query.filter_by(warehouse_id=warehouse_id, product_id=product_id).first()
    if balance:
        return balance
    product = db.session.get(Product, product_id)
    if product is None:
        raise ValueError('Product not found')
    # Initialize per-warehouse balance to 0 rather than mirroring the global product.quantity.
    # The global `Product.quantity` is the aggregate product stock; warehouse balances must be
    # updated through explicit transfer or stock allocation workflows.
    balance = WarehouseStock(warehouse_id=warehouse_id, product_id=product_id, quantity=0)
    db.session.add(balance)
    db.session.flush()
    return balance


def create_warehouse(name, code, address=None):
    warehouse = Warehouse(name=name, code=code.upper(), address=address)
    db.session.add(warehouse)
    db.session.flush()
    return warehouse


def _execute_stock_transfer(product_id, source_warehouse_id, destination_warehouse_id, quantity, user_id, *, note=None, transfer=None):
    if source_warehouse_id == destination_warehouse_id:
        raise ValueError('Source and destination warehouses must be different.')
    if quantity <= 0:
        raise ValueError('Transfer quantity must be positive.')

    with db.session.begin_nested():
        product = db.session.execute(
            select(Product).filter_by(id=product_id).with_for_update(nowait=False)
        ).scalar_one_or_none()
        if product is None:
            raise ValueError('Product not found')

        source = db.session.execute(
            select(WarehouseStock).filter_by(warehouse_id=source_warehouse_id, product_id=product_id).with_for_update(nowait=False)
        ).scalar_one_or_none()
        if source is None:
            raise ValueError('Source warehouse has no stock record for this product.')

        destination = db.session.execute(
            select(WarehouseStock).filter_by(warehouse_id=destination_warehouse_id, product_id=product_id).with_for_update(nowait=False)
        ).scalar_one_or_none()
        if destination is None:
            destination = WarehouseStock(warehouse_id=destination_warehouse_id, product_id=product_id, quantity=0)
            db.session.add(destination)
            db.session.flush()

        if quantity > source.quantity:
            raise ValueError('Transfer quantity exceeds source warehouse stock.')
        source.quantity -= quantity
        destination.quantity += quantity

        if source.quantity < 0 or destination.quantity < 0:
            raise ValueError('Warehouse stock levels cannot become negative.')

        if transfer is None:
            transfer = StockTransfer(
                transfer_number=next_transfer_number(),
                product_id=product_id,
                source_warehouse_id=source_warehouse_id,
                destination_warehouse_id=destination_warehouse_id,
                quantity=quantity,
                status='completed',
                note=note,
                created_by=user_id,
            )
            db.session.add(transfer)
            db.session.flush()
        else:
            transfer.status = 'completed'
            transfer.approved_at = utc_now()
            db.session.add(transfer)

        db.session.add(create_stock_movement(
            product,
            'transfer',
            0,
            user_id,
            reference_type='StockTransfer',
            reference_id=transfer.id,
            note=note or f'Transferred {quantity} units from warehouse {source_warehouse_id} to {destination_warehouse_id}',
            quantity_before=product.quantity,
        ))

    return transfer


def request_stock_transfer(product_id, source_warehouse_id, destination_warehouse_id, quantity, user_id, *, note=None):
    if source_warehouse_id == destination_warehouse_id:
        raise ValueError('Source and destination warehouses must be different.')
    if quantity <= 0:
        raise ValueError('Transfer quantity must be positive.')

    transfer = StockTransfer(
        transfer_number=next_transfer_number(),
        product_id=product_id,
        source_warehouse_id=source_warehouse_id,
        destination_warehouse_id=destination_warehouse_id,
        quantity=quantity,
        status='pending',
        note=note,
        created_by=user_id,
    )
    db.session.add(transfer)
    db.session.flush()
    log_operation_timeline(
        user_id,
        'StockTransfer',
        transfer.id,
        'created',
        comment=f'Requested transfer {transfer.transfer_number}',
        extra={'status': transfer.status, 'quantity': transfer.quantity},
    )
    return transfer


def approve_stock_transfer(transfer_id, approver_id, *, note=None):
    transfer = db.session.get(StockTransfer, transfer_id)
    if transfer is None:
        raise ValueError('Transfer not found.')
    if transfer.status != 'pending':
        raise ValueError('Only pending transfers can be approved.')
    transfer.approved_by = approver_id
    transfer.approved_at = utc_now()
    result = _execute_stock_transfer(
        transfer.product_id,
        transfer.source_warehouse_id,
        transfer.destination_warehouse_id,
        transfer.quantity,
        approver_id,
        note=note or transfer.note,
        transfer=transfer,
    )
    log_operation_timeline(
        approver_id,
        'StockTransfer',
        transfer.id,
        'approved',
        comment=f'Approved transfer {transfer.transfer_number}',
        extra={'status': result.status, 'quantity': result.quantity},
    )
    return result


def reject_stock_transfer(transfer_id, approver_id, reason=None):
    transfer = db.session.get(StockTransfer, transfer_id)
    if transfer is None:
        raise ValueError('Transfer not found.')
    if transfer.status != 'pending':
        raise ValueError('Only pending transfers can be rejected.')
    transfer.status = 'rejected'
    transfer.rejection_reason = reason
    transfer.approved_by = approver_id
    transfer.approved_at = utc_now()
    log_operation_timeline(
        approver_id,
        'StockTransfer',
        transfer.id,
        'rejected',
        comment=reason or f'Rejected transfer {transfer.transfer_number}',
        extra={'status': transfer.status},
    )
    return transfer


def cancel_stock_transfer(transfer_id, user_id, reason=None):
    transfer = db.session.get(StockTransfer, transfer_id)
    if transfer is None:
        raise ValueError('Transfer not found.')
    if transfer.status != 'pending':
        raise ValueError('Only pending transfers can be cancelled.')
    transfer.status = 'cancelled'
    transfer.cancellation_reason = reason
    transfer.approved_by = user_id
    transfer.approved_at = utc_now()
    log_operation_timeline(
        user_id,
        'StockTransfer',
        transfer.id,
        'cancelled',
        comment=reason or f'Cancelled transfer {transfer.transfer_number}',
        extra={'status': transfer.status},
    )
    return transfer


def reverse_transfer(transfer_id, user_id, *, note=None):
    transfer = db.session.get(StockTransfer, transfer_id)
    if transfer is None:
        raise ValueError('Transfer not found.')
    if transfer.status != 'completed':
        raise ValueError('Only completed transfers can be reversed.')

    with db.session.begin_nested():
        product = db.session.execute(
            select(Product).filter_by(id=transfer.product_id).with_for_update(nowait=False)
        ).scalar_one_or_none()
        if product is None:
            raise ValueError('Product not found')

        source = db.session.execute(
            select(WarehouseStock).filter_by(warehouse_id=transfer.source_warehouse_id, product_id=transfer.product_id).with_for_update(nowait=False)
        ).scalar_one_or_none()
        destination = db.session.execute(
            select(WarehouseStock).filter_by(warehouse_id=transfer.destination_warehouse_id, product_id=transfer.product_id).with_for_update(nowait=False)
        ).scalar_one_or_none()

        if source is None or destination is None:
            raise ValueError('Cannot reverse transfer when warehouse stock records are missing.')
        if destination.quantity < transfer.quantity:
            raise ValueError('Destination warehouse does not have enough stock to reverse the transfer.')

        destination.quantity -= transfer.quantity
        source.quantity += transfer.quantity

        if source.quantity < 0 or destination.quantity < 0:
            raise ValueError('Warehouse stock levels cannot become negative.')

        transfer.status = 'cancelled'
        db.session.add(create_stock_movement(
            product,
            'transfer',
            0,
            user_id,
            reference_type='StockTransfer',
            reference_id=transfer.id,
            note=note or f'Reversed transfer {transfer.transfer_number}',
            quantity_before=product.quantity,
        ))
    log_operation_timeline(
        user_id,
        'StockTransfer',
        transfer.id,
        'reversed',
        comment=note or f'Reversed transfer {transfer.transfer_number}',
        extra={'status': transfer.status},
    )

    return transfer


def compute_warehouse_total_for_product(product_id):
    """Return the total quantity of a product across all warehouse balances."""
    total = db.session.query(db.func.coalesce(db.func.sum(WarehouseStock.quantity), 0)).filter(WarehouseStock.product_id == product_id).scalar()
    return int(total or 0)


def product_warehouse_consistency(product_id):
    """Compare `Product.quantity` with sum of `WarehouseStock` quantities and return a dict with results.

    This helps detect inconsistencies when warehouse balances were initialized or modified improperly.
    """
    from app.models import Product

    product = db.session.get(Product, product_id)
    if product is None:
        raise ValueError('Product not found')
    warehouse_total = compute_warehouse_total_for_product(product_id)
    return {
        'product_id': product_id,
        'product_quantity': int(product.quantity),
        'warehouse_total': warehouse_total,
        'consistent': int(product.quantity) == warehouse_total,
    }
