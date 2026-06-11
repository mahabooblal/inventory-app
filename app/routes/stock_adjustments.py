from flask import Blueprint, flash, redirect, render_template, url_for, abort
from flask_login import current_user, login_required

from app import db
from app.forms import StockAdjustmentForm
from app.models import OperationTimeline, Product, StockAdjustment
from app.services.activity_service import log_activity
from app.services.notification_service import notify_role_users, create_notification
from app.services.stock_adjustment_service import (
    approve_stock_adjustment,
    cancel_stock_adjustment,
    reject_stock_adjustment,
    request_stock_adjustment,
)
from app.utils.permissions import admin_required, manager_required, roles_required

bp = Blueprint('stock_adjustments', __name__, url_prefix='/stock-adjustments')


def load_product_choices(form):
    form.product_id.choices = [(product.id, f'{product.name} ({product.quantity} available)') for product in Product.query.order_by(Product.name).all()]


@bp.route('/', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager')
def list_adjustments():
    form = StockAdjustmentForm()
    load_product_choices(form)
    if form.validate_on_submit():
        try:
            adjustment = request_stock_adjustment(
                form.product_id.data,
                form.adjustment_type.data,
                form.quantity_delta.data,
                form.reason.data,
                current_user.id,
            )
            log_activity(current_user.id, 'CREATE', 'StockAdjustment', adjustment.id, f'Requested stock adjustment for {adjustment.product.name}')
            notify_role_users(['admin'], f'Approval required: stock adjustment request for {adjustment.product.name}', 'warning')
            db.session.commit()
            flash('Stock adjustment submitted for approval.', 'success')
            return redirect(url_for('stock_adjustments.list_adjustments'))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), 'danger')

    adjustments = StockAdjustment.query.order_by(StockAdjustment.created_at.desc()).limit(100).all()
    return render_template('stock_adjustments/list.html', title='Stock Adjustments', form=form, adjustments=adjustments)


@bp.route('/<int:adjustment_id>')
@login_required
@roles_required('admin', 'manager')
def detail(adjustment_id):
    adjustment = db.session.get(StockAdjustment, adjustment_id)
    if adjustment is None:
        abort(404)
    timeline = OperationTimeline.query.filter_by(entity_type='StockAdjustment', entity_id=adjustment.id).order_by(OperationTimeline.timestamp.asc()).all()
    return render_template('stock_adjustments/detail.html', title=f'Adjustment {adjustment.id}', adjustment=adjustment, timeline=timeline)


@bp.route('/<int:adjustment_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve(adjustment_id):
    try:
        adjustment = approve_stock_adjustment(adjustment_id, current_user.id)
        log_activity(current_user.id, 'APPROVE', 'StockAdjustment', adjustment.id, f'Approved adjustment for {adjustment.product.name}')
        create_notification(adjustment.requester.id, f'Your adjustment request for {adjustment.product.name} was approved.', 'success')
        db.session.commit()
        flash('Stock adjustment approved and ledger updated.', 'success')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('stock_adjustments.list_adjustments'))


@bp.route('/<int:adjustment_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject(adjustment_id):
    try:
        adjustment = reject_stock_adjustment(adjustment_id, current_user.id, reason=request.form.get('reason'))
        log_activity(current_user.id, 'REJECT', 'StockAdjustment', adjustment.id, f'Rejected adjustment for {adjustment.product.name}')
        create_notification(adjustment.requester.id, f'Your adjustment request for {adjustment.product.name} was rejected.', 'danger')
        db.session.commit()
        flash('Stock adjustment rejected.', 'info')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('stock_adjustments.list_adjustments'))


@bp.route('/<int:adjustment_id>/cancel', methods=['POST'])
@login_required
def cancel(adjustment_id):
    try:
        adjustment = db.session.get(StockAdjustment, adjustment_id)
        if adjustment is None:
            raise ValueError('Stock adjustment not found')
        if adjustment.requested_by != current_user.id and not current_user.is_admin():
            raise ValueError('Not authorized to cancel this adjustment request.')
        adjustment = cancel_stock_adjustment(adjustment_id, current_user.id, reason=request.form.get('reason'))
        log_activity(current_user.id, 'CANCEL', 'StockAdjustment', adjustment.id, f'Cancelled adjustment request for {adjustment.product.name}')
        db.session.commit()
        flash('Stock adjustment request cancelled.', 'info')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('stock_adjustments.list_adjustments'))
