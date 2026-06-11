from flask import Blueprint, flash, redirect, render_template, url_for, abort
from flask_login import current_user, login_required

from app import db
from app.forms import ReturnOrderForm
from app.models import Customer, OperationTimeline, Product, ReturnOrder, Supplier
from app.services.activity_service import log_activity
from app.services.notification_service import create_notification, notify_role_users
from app.services.return_service import (
    request_return,
    approve_return,
    reject_return,
    cancel_return,
)
from app.utils.permissions import roles_required

bp = Blueprint('returns', __name__, url_prefix='/returns')


def load_choices(form):
    form.product_id.choices = [(p.id, f'{p.name} ({p.quantity} available)') for p in Product.query.order_by(Product.name).all()]
    form.customer_id.choices = [(0, 'No Customer')] + [(c.id, c.name) for c in Customer.query.order_by(Customer.name).all()]
    form.supplier_id.choices = [(0, 'No Supplier')] + [(s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()]


@bp.route('/', methods=['GET', 'POST'])
@login_required
def list_returns():
    form = ReturnOrderForm()
    load_choices(form)
    if form.validate_on_submit():
        try:
            return_order = request_return(
                form.return_type.data,
                form.product_id.data,
                form.quantity.data,
                current_user.id,
                customer_id=form.customer_id.data or None,
                supplier_id=form.supplier_id.data or None,
                refund_amount=form.refund_amount.data or 0,
                restock=form.restock.data,
                reason=form.reason.data,
            )
            log_activity(current_user.id, 'CREATE', 'ReturnOrder', return_order.id, f'Requested return {return_order.return_number}')
            notify_role_users(['admin', 'manager'], f'New return request {return_order.return_number} awaiting approval', 'info')
            db.session.commit()
            flash('Return request submitted for approval.', 'success')
            return redirect(url_for('returns.list_returns'))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), 'danger')
    returns = ReturnOrder.query.order_by(ReturnOrder.created_at.desc()).limit(100).all()
    return render_template('returns/list.html', title='Returns', form=form, returns=returns)


@bp.route('/<int:return_order_id>')
@login_required
def detail(return_order_id):
    return_order = db.session.get(ReturnOrder, return_order_id)
    if return_order is None:
        abort(404)
    timeline = OperationTimeline.query.filter_by(entity_type='ReturnOrder', entity_id=return_order.id).order_by(OperationTimeline.timestamp.asc()).all()
    return render_template('returns/detail.html', title=return_order.return_number, return_order=return_order, timeline=timeline)


@bp.route('/<int:return_order_id>/approve', methods=['POST'])
@login_required
@roles_required('admin', 'manager')
def approve(return_order_id):
    return_order = db.session.get(ReturnOrder, return_order_id)
    if return_order is None:
        flash('Return order not found.', 'danger')
        return redirect(url_for('returns.list_returns'))
    
    if not current_user.is_admin() and return_order.created_by != current_user.id:
        flash('You do not have permission to approve this return.', 'danger')
        return redirect(url_for('returns.list_returns'))
    
    try:
        return_order = approve_return(return_order_id, current_user.id)
        log_activity(current_user.id, 'APPROVE', 'ReturnOrder', return_order.id, f'Approved return {return_order.return_number}')
        requester = return_order.requester
        if requester:
            create_notification(requester.id, f'Your return request {return_order.return_number} has been approved', 'success')
        db.session.commit()
        flash('Return approved and processed.', 'success')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('returns.list_returns'))


@bp.route('/<int:return_order_id>/reject', methods=['POST'])
@login_required
@roles_required('admin', 'manager')
def reject(return_order_id):
    return_order = db.session.get(ReturnOrder, return_order_id)
    if return_order is None:
        flash('Return order not found.', 'danger')
        return redirect(url_for('returns.list_returns'))
    
    if not current_user.is_admin() and return_order.created_by != current_user.id:
        flash('You do not have permission to reject this return.', 'danger')
        return redirect(url_for('returns.list_returns'))
    
    try:
        return_order = reject_return(return_order_id, current_user.id, reason=request.form.get('reason'))
        log_activity(current_user.id, 'REJECT', 'ReturnOrder', return_order.id, f'Rejected return {return_order.return_number}')
        requester = return_order.requester
        if requester:
            create_notification(requester.id, f'Your return request {return_order.return_number} has been rejected', 'danger')
        db.session.commit()
        flash('Return rejected.', 'success')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('returns.list_returns'))


@bp.route('/<int:return_order_id>/cancel', methods=['POST'])
@login_required
def cancel(return_order_id):
    return_order = db.session.get(ReturnOrder, return_order_id)
    if return_order is None:
        flash('Return order not found.', 'danger')
        return redirect(url_for('returns.list_returns'))
    
    # Only the requester or admin can cancel
    if return_order.created_by != current_user.id and not current_user.is_admin():
        flash('You do not have permission to cancel this return.', 'danger')
        return redirect(url_for('returns.list_returns'))
    
    try:
        return_order = cancel_return(return_order_id, current_user.id, reason=request.form.get('reason'))
        log_activity(current_user.id, 'CANCEL', 'ReturnOrder', return_order.id, f'Cancelled return {return_order.return_number}')
        db.session.commit()
        flash('Return cancelled.', 'success')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('returns.list_returns'))
