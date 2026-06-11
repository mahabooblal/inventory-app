from sqlalchemy import select

from app import db
from app.models import Product, Sale, StockIn, StockMovement
from app.services.email_service import send_low_stock_alert


def create_stock_movement(product, movement_type, quantity, user_id, *, reference_type=None, reference_id=None, note=None, unit_cost=0, batch_reference=None, expires_on=None, quantity_before=None):
    quantity_before = product.quantity if quantity_before is None else quantity_before
    return StockMovement(
        product_id=product.id,
        movement_type=movement_type,
        quantity=quantity,
        quantity_before=quantity_before,
        quantity_after=quantity_before + quantity,
        reference_type=reference_type,
        reference_id=reference_id,
        note=note,
        unit_cost=unit_cost or 0,
        batch_reference=batch_reference,
        expires_on=expires_on,
        created_by=user_id,
    )


def add_stock(product_id, supplier_id, quantity, note, user_id, *, batch_reference=None, expires_on=None, receive_date=None, unit_cost=0, reference_type='StockIn', reference_id=None, commit=True):
    """Increase product stock and save a stock-in history record."""
    # use a transaction to ensure atomic update
    with db.session.begin_nested():
        product = db.session.execute(
            select(Product).filter_by(id=product_id).with_for_update(nowait=False)
        ).scalar_one_or_none()
        if product is None:
            raise ValueError('Product not found')
        quantity_before = product.quantity
        product.quantity += quantity

        stock_entry = StockIn(
            product_id=product_id,
            supplier_id=supplier_id,
            batch_reference=batch_reference,
            expires_on=expires_on,
            receive_date=receive_date,
            quantity=quantity,
            unit_cost=unit_cost,
            note=note,
            created_by=user_id,
        )
        db.session.add(stock_entry)
        db.session.flush()
        db.session.add(create_stock_movement(
            product,
            'incoming',
            quantity,
            user_id,
            reference_type=reference_type,
            reference_id=reference_id or stock_entry.id,
            note=note,
            unit_cost=unit_cost,
            batch_reference=batch_reference,
            expires_on=expires_on,
            quantity_before=quantity_before,
        ))

    if commit:
        db.session.commit()
    return stock_entry


def record_sale(product_id, quantity, selling_price, user_id, customer_id=None, *, destination_details=None, commit=True):
    """Decrease product stock after checking enough quantity exists."""
    # perform check and update inside a read-locked transaction to avoid race conditions
    with db.session.begin_nested():
        product = db.session.execute(
            select(Product).filter_by(id=product_id).with_for_update(nowait=False)
        ).scalar_one_or_none()
        if product is None:
            raise ValueError('Product not found')

        if quantity > product.quantity:
            raise ValueError('Sale quantity cannot be greater than available stock.')

        quantity_before = product.quantity
        product.quantity -= quantity
        sale = Sale(
            product_id=product_id,
            customer_id=customer_id,
            quantity=quantity,
            selling_price=selling_price,
            total_amount=quantity * selling_price,
            destination_details=destination_details,
            created_by=user_id,
        )
        db.session.add(sale)
        db.session.flush()
        db.session.add(create_stock_movement(
            product,
            'outgoing',
            -quantity,
            user_id,
            reference_type='Sale',
            reference_id=sale.id,
            note=destination_details,
            quantity_before=quantity_before,
        ))

        should_alert = product.quantity <= product.low_stock_limit

    # send alerts after commit to avoid holding the transaction open
    if should_alert:
        send_low_stock_alert(product.name, product.quantity, product.low_stock_limit)

    if commit:
        db.session.commit()
    return sale
