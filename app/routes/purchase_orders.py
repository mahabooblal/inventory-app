from flask import Blueprint, flash, redirect, render_template, request, url_for, abort
from flask_login import current_user, login_required

from app import db
from app.forms import PurchaseOrderForm, PurchaseOrderReceiveForm
from app.models import OperationTimeline, Product, PurchaseOrder, Supplier
from app.services.activity_service import log_activity
from app.services.notification_service import create_notification, notify_role_users
from app.services.purchase_order_service import (
    create_purchase_order,
    receive_purchase_order,
    submit_purchase_order,
    approve_purchase_order,
    reject_purchase_order,
    cancel_purchase_order,
)
from app.utils.permissions import manager_required, roles_required

bp = Blueprint('purchase_orders', __name__, url_prefix='/purchase-orders')


def load_supplier_choices(form):
    form.supplier_id.choices = [(supplier.id, supplier.name) for supplier in Supplier.query.order_by(Supplier.name).all()]


@bp.route('/')
@login_required
@roles_required('admin', 'manager')
def list_purchase_orders():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '').strip()
    query = PurchaseOrder.query
    if status:
        query = query.filter(PurchaseOrder.status == status)
    pagination = query.order_by(PurchaseOrder.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('purchase_orders/list.html', title='Purchase Orders', purchase_orders=pagination.items, pagination=pagination, status=status)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@manager_required
def create():
    if Supplier.query.count() == 0 or Product.query.count() == 0:
        flash('Add at least one supplier and product before creating purchase orders.', 'warning')
        return redirect(url_for('purchase_orders.list_purchase_orders'))

    form = PurchaseOrderForm()
    load_supplier_choices(form)
    products = Product.query.order_by(Product.name).all()

    if form.validate_on_submit():
        items = []
        product_ids = request.form.getlist('product_id')
        quantities = request.form.getlist('quantity_ordered')
        unit_costs = request.form.getlist('unit_cost')
        for product_id, quantity, unit_cost in zip(product_ids, quantities, unit_costs):
            items.append({'product_id': product_id, 'quantity_ordered': quantity, 'unit_cost': unit_cost})
        try:
            purchase_order = create_purchase_order(
                form.supplier_id.data,
                items,
                current_user.id,
                expected_date=form.expected_date.data,
                notes=form.notes.data,
            )
            log_activity(current_user.id, 'CREATE', 'PurchaseOrder', purchase_order.id, f'Created {purchase_order.po_number}')
            db.session.commit()
            flash('Purchase order created.', 'success')
            return redirect(url_for('purchase_orders.detail', purchase_order_id=purchase_order.id))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), 'danger')

    return render_template('purchase_orders/form.html', title='Create Purchase Order', form=form, products=products)


@bp.route('/<int:purchase_order_id>')
@login_required
@roles_required('admin', 'manager')
def detail(purchase_order_id):
    purchase_order = db.session.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        abort(404)
    form = PurchaseOrderReceiveForm()
    timeline = OperationTimeline.query.filter_by(entity_type='PurchaseOrder', entity_id=purchase_order.id).order_by(OperationTimeline.timestamp.asc()).all()
    return render_template('purchase_orders/detail.html', title=purchase_order.po_number, purchase_order=purchase_order, form=form, timeline=timeline)


@bp.route('/<int:purchase_order_id>/receive', methods=['POST'])
@login_required
@manager_required
def receive(purchase_order_id):
    form = PurchaseOrderReceiveForm()
    purchase_order = db.session.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        abort(404)
    if form.validate_on_submit():
        quantities = {
            key.replace('receive_qty_', ''): value
            for key, value in request.form.items()
            if key.startswith('receive_qty_')
        }
        try:
            receive_purchase_order(
                purchase_order.id,
                quantities,
                current_user.id,
                batch_reference=form.batch_reference.data,
            )
            log_activity(current_user.id, 'UPDATE', 'PurchaseOrder', purchase_order.id, f'Received stock against {purchase_order.po_number}')
            db.session.commit()
            flash('Purchase order stock received.', 'success')
        except ValueError as error:
            db.session.rollback()
            flash(str(error), 'danger')
    return redirect(url_for('purchase_orders.detail', purchase_order_id=purchase_order_id))


@bp.route('/<int:purchase_order_id>/submit', methods=['POST'])
@login_required
@manager_required
def submit(purchase_order_id):
    purchase_order = db.session.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        flash('Purchase order not found.', 'danger')
        return redirect(url_for('purchase_orders.list_purchase_orders'))
    
    try:
        purchase_order = submit_purchase_order(purchase_order_id, current_user.id)
        log_activity(current_user.id, 'SUBMIT', 'PurchaseOrder', purchase_order.id, f'Submitted {purchase_order.po_number} for approval')
        notify_role_users(['admin', 'manager'], f'Purchase order {purchase_order.po_number} awaiting approval', 'info')
        db.session.commit()
        flash('Purchase order submitted for approval.', 'success')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('purchase_orders.detail', purchase_order_id=purchase_order_id))


@bp.route('/<int:purchase_order_id>/approve', methods=['POST'])
@login_required
@roles_required('admin', 'manager')
def approve(purchase_order_id):
    purchase_order = db.session.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        flash('Purchase order not found.', 'danger')
        return redirect(url_for('purchase_orders.list_purchase_orders'))
    
    if not current_user.is_admin() and purchase_order.created_by != current_user.id:
        flash('You do not have permission to approve this purchase order.', 'danger')
        return redirect(url_for('purchase_orders.detail', purchase_order_id=purchase_order_id))
    
    try:
        purchase_order = approve_purchase_order(purchase_order_id, current_user.id)
        log_activity(current_user.id, 'APPROVE', 'PurchaseOrder', purchase_order.id, f'Approved {purchase_order.po_number}')
        requester = purchase_order.requester
        if requester:
            create_notification(requester.id, f'Your purchase order {purchase_order.po_number} has been approved', 'success')
        db.session.commit()
        flash('Purchase order approved.', 'success')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('purchase_orders.detail', purchase_order_id=purchase_order_id))


@bp.route('/<int:purchase_order_id>/reject', methods=['POST'])
@login_required
@roles_required('admin', 'manager')
def reject(purchase_order_id):
    purchase_order = db.session.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        flash('Purchase order not found.', 'danger')
        return redirect(url_for('purchase_orders.list_purchase_orders'))
    
    if not current_user.is_admin() and purchase_order.created_by != current_user.id:
        flash('You do not have permission to reject this purchase order.', 'danger')
        return redirect(url_for('purchase_orders.detail', purchase_order_id=purchase_order_id))
    
    try:
        purchase_order = reject_purchase_order(purchase_order_id, current_user.id, reason=request.form.get('reason'))
        log_activity(current_user.id, 'REJECT', 'PurchaseOrder', purchase_order.id, f'Rejected {purchase_order.po_number}')
        requester = purchase_order.requester
        if requester:
            create_notification(requester.id, f'Your purchase order {purchase_order.po_number} has been rejected', 'danger')
        db.session.commit()
        flash('Purchase order rejected.', 'success')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('purchase_orders.detail', purchase_order_id=purchase_order_id))


@bp.route('/<int:purchase_order_id>/cancel', methods=['POST'])
@login_required
def cancel(purchase_order_id):
    purchase_order = db.session.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        flash('Purchase order not found.', 'danger')
        return redirect(url_for('purchase_orders.list_purchase_orders'))
    
    # Only the requester or admin can cancel
    if purchase_order.created_by != current_user.id and not current_user.is_admin():
        flash('You do not have permission to cancel this purchase order.', 'danger')
        return redirect(url_for('purchase_orders.detail', purchase_order_id=purchase_order_id))
    
    try:
        purchase_order = cancel_purchase_order(purchase_order_id, current_user.id, reason=request.form.get('reason'))
        log_activity(current_user.id, 'CANCEL', 'PurchaseOrder', purchase_order.id, f'Cancelled {purchase_order.po_number}')
        db.session.commit()
        flash('Purchase order cancelled.', 'success')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('purchase_orders.detail', purchase_order_id=purchase_order_id))
