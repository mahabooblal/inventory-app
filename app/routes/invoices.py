from flask import Blueprint, flash, redirect, render_template, request, url_for, abort
from flask_login import current_user, login_required

from app import db
from app.forms import InvoiceForm, PaymentForm
from app.models import Customer, Invoice, OperationTimeline, Product
from app.services import export_service
from app.services.activity_service import log_activity
from app.services.invoice_service import create_invoice, record_payment

bp = Blueprint('invoices', __name__, url_prefix='/invoices')


@bp.route('/')
@login_required
def list_invoices():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '').strip()
    query = Invoice.query
    if status:
        query = query.filter(Invoice.status == status)
    pagination = query.order_by(Invoice.issued_at.desc()).paginate(page=page, per_page=25, error_out=False)
    return render_template('invoices/list.html', title='Invoices', invoices=pagination.items, pagination=pagination, status=status)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    if Product.query.count() == 0:
        flash('Add products before creating invoices.', 'warning')
        return redirect(url_for('products.list_products'))

    form = InvoiceForm()
    form.customer_id.choices = [(0, 'Walk-in Customer')] + [(customer.id, customer.name) for customer in Customer.query.order_by(Customer.name).all()]
    products = Product.query.filter(Product.is_active.is_(True)).order_by(Product.name).all()

    if form.validate_on_submit():
        items = []
        for product_id, quantity, unit_price, discount_amount, tax_rate in zip(
            request.form.getlist('product_id'),
            request.form.getlist('quantity'),
            request.form.getlist('unit_price'),
            request.form.getlist('discount_amount'),
            request.form.getlist('tax_rate'),
        ):
            items.append({
                'product_id': product_id,
                'quantity': quantity,
                'unit_price': unit_price,
                'discount_amount': discount_amount,
                'tax_rate': tax_rate,
            })
        try:
            invoice = create_invoice(
                form.customer_id.data if form.customer_id.data else None,
                items,
                current_user.id,
                notes=form.notes.data,
                payment_amount=form.payment_amount.data or 0,
                payment_method=form.payment_method.data,
            )
            log_activity(current_user.id, 'CREATE', 'Invoice', invoice.id, f'Created invoice {invoice.invoice_number}')
            db.session.commit()
            flash('Invoice created and stock deducted.', 'success')
            return redirect(url_for('invoices.detail', invoice_id=invoice.id))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), 'danger')

    product_meta = {product.id: {'price': float(product.price), 'quantity': product.quantity, 'name': product.name} for product in products}
    return render_template('invoices/form.html', title='Create Invoice', form=form, products=products, product_meta=product_meta)


@bp.route('/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
def detail(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if invoice is None:
        abort(404)
    form = PaymentForm()
    if form.validate_on_submit():
        try:
            payment = record_payment(invoice.id, form.amount.data, form.method.data, current_user.id, reference=form.reference.data)
            log_activity(current_user.id, 'CREATE', 'Payment', payment.id, f'Recorded payment for {invoice.invoice_number}')
            db.session.commit()
            flash('Payment recorded.', 'success')
            return redirect(url_for('invoices.detail', invoice_id=invoice.id))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), 'danger')

    timeline = OperationTimeline.query.filter_by(entity_type='Invoice', entity_id=invoice.id).order_by(OperationTimeline.timestamp.asc()).all()
    return render_template('invoices/detail.html', title=invoice.invoice_number, invoice=invoice, form=form, timeline=timeline)


@bp.route('/<int:invoice_id>/pdf')
@login_required
def pdf(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if invoice is None:
        abort(404)
    return export_service.invoice_pdf_response(invoice)
