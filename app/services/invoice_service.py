from decimal import Decimal, ROUND_HALF_UP

from app import db
from app.models import Invoice, InvoiceItem, Payment, Product
from app.services.inventory_service import create_stock_movement
from app.utils.datetime import utc_now


def money_decimal(value):
    return Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def next_invoice_number():
    next_id = (db.session.query(db.func.max(Invoice.id)).scalar() or 0) + 1
    return f'INV-{utc_now().strftime("%Y%m%d")}-{next_id:05d}'


def invoice_status(invoice):
    if invoice.amount_paid <= 0:
        return 'issued'
    if invoice.amount_paid >= invoice.total_amount:
        return 'paid'
    return 'partially_paid'


def create_invoice(customer_id, items, user_id, *, notes=None, payment_amount=0, payment_method='cash'):
    clean_items = []
    for item in items:
        product_id = int(item.get('product_id') or 0)
        quantity = int(item.get('quantity') or 0)
        unit_price = money_decimal(item.get('unit_price') or 0)
        discount_amount = money_decimal(item.get('discount_amount') or 0)
        tax_rate = money_decimal(item.get('tax_rate') or 0)
        if product_id and quantity > 0:
            clean_items.append((product_id, quantity, unit_price, discount_amount, tax_rate))
    if not clean_items:
        raise ValueError('Add at least one invoice item.')

    with db.session.begin_nested():
        invoice = Invoice(
            invoice_number=next_invoice_number(),
            customer_id=customer_id or None,
            status='issued',
            notes=notes,
            created_by=user_id,
        )
        db.session.add(invoice)
        db.session.flush()

        subtotal = Decimal('0.00')
        discount_total = Decimal('0.00')
        tax_total = Decimal('0.00')

        for product_id, quantity, unit_price, discount_amount, tax_rate in clean_items:
            product = db.session.get(Product, product_id)
            if product is None:
                raise ValueError('Product not found')
            if quantity > product.quantity:
                raise ValueError(f'Insufficient stock for {product.name}.')

            gross = money_decimal(unit_price * quantity)
            discount = min(discount_amount, gross)
            taxable = gross - discount
            tax_amount = money_decimal(taxable * tax_rate / Decimal('100'))
            line_total = taxable + tax_amount

            quantity_before = product.quantity
            product.quantity -= quantity
            db.session.add(InvoiceItem(
                invoice_id=invoice.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                discount_amount=discount,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                line_total=line_total,
            ))
            db.session.add(create_stock_movement(
                product,
                'outgoing',
                -quantity,
                user_id,
                reference_type='Invoice',
                reference_id=invoice.id,
                note=f'Invoice {invoice.invoice_number}',
                quantity_before=quantity_before,
            ))

            subtotal += gross
            discount_total += discount
            tax_total += tax_amount

        invoice.subtotal = subtotal
        invoice.discount_amount = discount_total
        invoice.tax_amount = tax_total
        invoice.total_amount = subtotal - discount_total + tax_total

        initial_payment = min(money_decimal(payment_amount), invoice.total_amount)
        if initial_payment > 0:
            db.session.add(Payment(
                invoice_id=invoice.id,
                amount=initial_payment,
                method=payment_method,
                received_by=user_id,
            ))
            invoice.amount_paid = initial_payment
        invoice.status = invoice_status(invoice)

    return invoice


def record_payment(invoice_id, amount, method, user_id, *, reference=None):
    invoice = db.session.get(Invoice, invoice_id)
    if invoice is None:
        raise ValueError('Invoice not found')
    if invoice.status == 'cancelled':
        raise ValueError('Cannot record payment for a cancelled invoice.')
    amount = money_decimal(amount)
    if amount <= 0:
        raise ValueError('Payment amount must be positive.')
    if amount > invoice.balance_due:
        raise ValueError('Payment amount cannot exceed invoice balance.')

    payment = Payment(
        invoice_id=invoice.id,
        amount=amount,
        method=method,
        reference=reference,
        received_by=user_id,
    )
    db.session.add(payment)
    invoice.amount_paid = money_decimal(invoice.amount_paid + amount)
    invoice.status = invoice_status(invoice)
    return payment
