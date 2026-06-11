from flask import Blueprint, flash, redirect, render_template, request, url_for, abort
from flask_login import current_user, login_required

from app import db
from app.forms import StockTransferForm, WarehouseForm
from app.models import OperationTimeline, Product, StockTransfer, Warehouse, WarehouseStock
from app.services.activity_service import log_activity
from app.services.notification_service import create_notification, notify_role_users
from app.services.warehouse_service import (
    create_warehouse,
    get_or_create_default_warehouse,
    request_stock_transfer,
    approve_stock_transfer,
    reject_stock_transfer,
    cancel_stock_transfer,
)
from app.utils.permissions import manager_required, roles_required

bp = Blueprint('warehouses', __name__, url_prefix='/warehouses')


def load_transfer_choices(form):
    form.product_id.choices = [(p.id, f'{p.name} ({p.sku})') for p in Product.query.order_by(Product.name).all()]
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name).all()
    form.source_warehouse_id.choices = [(w.id, w.name) for w in warehouses]
    form.destination_warehouse_id.choices = [(w.id, w.name) for w in warehouses]


@bp.route('/', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager')
def list_warehouses():
    get_or_create_default_warehouse()
    form = WarehouseForm()
    if form.validate_on_submit():
        try:
            warehouse = create_warehouse(form.name.data, form.code.data, form.address.data)
            log_activity(current_user.id, 'CREATE', 'Warehouse', warehouse.id, f'Created warehouse {warehouse.name}')
            db.session.commit()
            flash('Warehouse saved.', 'success')
            return redirect(url_for('warehouses.list_warehouses'))
        except Exception:
            db.session.rollback()
            flash('Warehouse code or name already exists.', 'danger')
    warehouses = Warehouse.query.order_by(Warehouse.name).all()
    return render_template('warehouses/list.html', title='Warehouses', warehouses=warehouses, form=form)


@bp.route('/<int:warehouse_id>')
@login_required
@roles_required('admin', 'manager')
def detail(warehouse_id):
    warehouse = db.session.get(Warehouse, warehouse_id)
    if warehouse is None:
        abort(404)
    balances = WarehouseStock.query.filter_by(warehouse_id=warehouse.id).all()
    return render_template('warehouses/detail.html', title=warehouse.name, warehouse=warehouse, balances=balances)


@bp.route('/transfers', methods=['GET', 'POST'])
@login_required
@manager_required
def transfers():
    get_or_create_default_warehouse()
    form = StockTransferForm()
    load_transfer_choices(form)
    if form.validate_on_submit():
        try:
            transfer = request_stock_transfer(
                form.product_id.data,
                form.source_warehouse_id.data,
                form.destination_warehouse_id.data,
                form.quantity.data,
                current_user.id,
                note=form.note.data,
            )
            log_activity(current_user.id, 'CREATE', 'StockTransfer', transfer.id, f'Requested transfer {transfer.transfer_number}')
            notify_role_users(['admin', 'manager'], f'New stock transfer request {transfer.transfer_number} awaiting approval', 'info')
            db.session.commit()
            flash('Stock transfer request submitted for approval.', 'success')
            return redirect(url_for('warehouses.transfers'))
        except ValueError as error:
            db.session.rollback()
            flash(str(error), 'danger')
    transfers = StockTransfer.query.order_by(StockTransfer.created_at.desc()).limit(50).all()
    return render_template('warehouses/transfers.html', title='Stock Transfers', form=form, transfers=transfers)


@bp.route('/transfers/<int:transfer_id>')
@login_required
@roles_required('admin', 'manager')
def transfer_detail(transfer_id):
    transfer = db.session.get(StockTransfer, transfer_id)
    if transfer is None:
        abort(404)
    timeline = OperationTimeline.query.filter_by(entity_type='StockTransfer', entity_id=transfer.id).order_by(OperationTimeline.timestamp.asc()).all()
    return render_template('warehouses/transfer_detail.html', title=transfer.transfer_number, transfer=transfer, timeline=timeline)


@bp.route('/transfers/<int:transfer_id>/approve', methods=['POST'])
@login_required
@roles_required('admin', 'manager')
def approve_transfer(transfer_id):
    transfer = db.session.get(StockTransfer, transfer_id)
    if transfer is None:
        flash('Transfer not found.', 'danger')
        return redirect(url_for('warehouses.transfers'))
    
    if not current_user.is_admin() and transfer.created_by != current_user.id:
        flash('You do not have permission to approve this transfer.', 'danger')
        return redirect(url_for('warehouses.transfers'))
    
    try:
        transfer = approve_stock_transfer(transfer_id, current_user.id)
        log_activity(current_user.id, 'APPROVE', 'StockTransfer', transfer.id, f'Approved transfer {transfer.transfer_number}')
        requester = transfer.requester
        if requester:
            create_notification(requester.id, f'Your transfer request {transfer.transfer_number} has been approved', 'success')
        db.session.commit()
        flash('Transfer approved and executed.', 'success')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('warehouses.transfers'))


@bp.route('/transfers/<int:transfer_id>/reject', methods=['POST'])
@login_required
@roles_required('admin', 'manager')
def reject_transfer(transfer_id):
    transfer = db.session.get(StockTransfer, transfer_id)
    if transfer is None:
        flash('Transfer not found.', 'danger')
        return redirect(url_for('warehouses.transfers'))
    
    if not current_user.is_admin() and transfer.created_by != current_user.id:
        flash('You do not have permission to reject this transfer.', 'danger')
        return redirect(url_for('warehouses.transfers'))
    
    try:
        transfer = reject_stock_transfer(transfer_id, current_user.id, reason=request.form.get('reason'))
        log_activity(current_user.id, 'REJECT', 'StockTransfer', transfer.id, f'Rejected transfer {transfer.transfer_number}')
        requester = transfer.requester
        if requester:
            create_notification(requester.id, f'Your transfer request {transfer.transfer_number} has been rejected', 'danger')
        db.session.commit()
        flash('Transfer rejected.', 'success')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('warehouses.transfers'))


@bp.route('/transfers/<int:transfer_id>/cancel', methods=['POST'])
@login_required
def cancel_transfer(transfer_id):
    transfer = db.session.get(StockTransfer, transfer_id)
    if transfer is None:
        flash('Transfer not found.', 'danger')
        return redirect(url_for('warehouses.transfers'))
    
    # Only the requester or admin can cancel
    if transfer.created_by != current_user.id and not current_user.is_admin():
        flash('You do not have permission to cancel this transfer.', 'danger')
        return redirect(url_for('warehouses.transfers'))
    
    try:
        transfer = cancel_stock_transfer(transfer_id, current_user.id, reason=request.form.get('reason'))
        log_activity(current_user.id, 'CANCEL', 'StockTransfer', transfer.id, f'Cancelled transfer {transfer.transfer_number}')
        db.session.commit()
        flash('Transfer cancelled.', 'success')
    except ValueError as error:
        db.session.rollback()
        flash(str(error), 'danger')
    return redirect(url_for('warehouses.transfers'))
