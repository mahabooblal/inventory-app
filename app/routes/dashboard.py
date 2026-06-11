from datetime import date, datetime, time, timedelta, timezone

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from app.utils.datetime import utc_now
from app.utils.permissions import roles_required

from sqlalchemy import func

from app import db
from app.models import Category, Customer, Product, Sale, StockIn, StockMovement, Supplier, PurchaseOrder, StockTransfer, ReturnOrder, StockAdjustment
from app.services.report_service import low_stock_products
from app.services.dashboard_service import (
    get_monthly_sales_data, get_inventory_status, get_top_selling_products,
    get_category_distribution, get_recent_activity, get_reorder_suggestions,
)
from app.services.purchase_order_service import approve_purchase_order, reject_purchase_order
from app.services.stock_adjustment_service import approve_stock_adjustment, reject_stock_adjustment
from app.services.return_service import approve_return, reject_return
from app.services.warehouse_service import approve_stock_transfer, reject_stock_transfer
from app.services.reconciliation_service import find_mismatched_products
import json

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@bp.route('/dashboard')
@login_required
@roles_required('admin', 'manager')
def index():
    # Basic stats
    today_start = datetime.combine(date.today(), time.min)
    tomorrow_start = today_start + timedelta(days=1)
    total_products = Product.query.count()
    total_stock_quantity = db.session.query(func.coalesce(func.sum(Product.quantity), 0)).scalar() or 0
    total_categories = Category.query.count()
    total_suppliers = Supplier.query.count()
    total_customers = Customer.query.count()
    incoming_today = db.session.query(func.coalesce(func.sum(StockIn.quantity), 0)).filter(StockIn.created_at >= today_start, StockIn.created_at < tomorrow_start).scalar() or 0
    outgoing_today = db.session.query(func.coalesce(func.sum(Sale.quantity), 0)).filter(Sale.sale_date >= today_start, Sale.sale_date < tomorrow_start).scalar() or 0
    total_sales = db.session.query(func.coalesce(func.sum(Sale.total_amount), 0)).scalar() or 0
    inventory_value = db.session.query(func.coalesce(func.sum(Product.quantity * Product.price), 0)).scalar() or 0
    low_stock_count = Product.query.filter(Product.quantity <= Product.low_stock_limit).count()
    out_of_stock_count = Product.query.filter(Product.quantity == 0).count()
    recent_transactions = Sale.query.order_by(Sale.sale_date.desc()).limit(10).all()
    current_stock_levels = Product.query.order_by(Product.quantity.asc(), Product.name.asc()).limit(12).all()
    recent_stock_in = StockIn.query.order_by(StockIn.created_at.desc()).limit(6).all()
    recent_stock_out = Sale.query.order_by(Sale.sale_date.desc()).limit(6).all()
    low_stock_products_list = low_stock_products()
    reconciliation_issues = len(find_mismatched_products())
    today_activity_count = StockMovement.query.filter(StockMovement.created_at >= today_start, StockMovement.created_at < tomorrow_start).count()

    pending_adjustments = StockAdjustment.query.filter_by(status='pending').count()
    pending_transfers = StockTransfer.query.filter_by(status='pending').count()
    pending_purchase_orders = PurchaseOrder.query.filter_by(status='pending').count()
    pending_returns = ReturnOrder.query.filter_by(status='pending').count()
    approval_pending_count = pending_adjustments + pending_transfers + pending_purchase_orders + pending_returns
    sla_boundary = utc_now() - timedelta(hours=48)
    escalated_pending_count = (
        StockAdjustment.query.filter(StockAdjustment.status == 'pending', StockAdjustment.created_at < sla_boundary).count() +
        StockTransfer.query.filter(StockTransfer.status == 'pending', StockTransfer.created_at < sla_boundary).count() +
        PurchaseOrder.query.filter(PurchaseOrder.status == 'pending', PurchaseOrder.created_at < sla_boundary).count() +
        ReturnOrder.query.filter(ReturnOrder.status == 'pending', ReturnOrder.created_at < sla_boundary).count()
    )
    pending_orders = approval_pending_count

    # Dashboard analytics
    monthly_labels, monthly_revenue = get_monthly_sales_data()
    inventory_status_labels, inventory_status_values = get_inventory_status()
    top_product_labels, top_product_values = get_top_selling_products()
    category_labels, category_values = get_category_distribution()
    recent_activity = get_recent_activity()
    reorder_suggestions = get_reorder_suggestions()

    chart_data = {
        'monthly_labels': monthly_labels,
        'monthly_revenue': monthly_revenue,
        'top_product_labels': top_product_labels,
        'top_product_values': top_product_values,
        'category_labels': category_labels,
        'category_values': category_values,
        'inventory_status_labels': inventory_status_labels,
        'inventory_status_values': inventory_status_values,
    }

    movement_labels = []
    incoming_values = []
    outgoing_values = []
    stock_trend_values = []
    for day_offset in range(13, -1, -1):
        current_day = date.today() - timedelta(days=day_offset)
        day_start = datetime.combine(current_day, time.min)
        day_end = day_start + timedelta(days=1)
        movement_labels.append(current_day.strftime('%d %b'))
        incoming_values.append(int(db.session.query(func.coalesce(func.sum(StockIn.quantity), 0)).filter(StockIn.created_at >= day_start, StockIn.created_at < day_end).scalar() or 0))
        outgoing_values.append(int(db.session.query(func.coalesce(func.sum(Sale.quantity), 0)).filter(Sale.sale_date >= day_start, Sale.sale_date < day_end).scalar() or 0))
        stock_trend_values.append(max(0, int(total_stock_quantity) - sum(incoming_values) + sum(outgoing_values)))

    chart_data.update({
        'movement_labels': movement_labels,
        'incoming_values': incoming_values,
        'outgoing_values': outgoing_values,
        'stock_trend_values': stock_trend_values,
    })

    stats = {
        'total_products': total_products,
        'total_stock_quantity': total_stock_quantity,
        'incoming_today': incoming_today,
        'outgoing_today': outgoing_today,
        'total_categories': total_categories,
        'total_suppliers': total_suppliers,
        'total_customers': total_customers,
        'total_sales': total_sales,
        'inventory_value': inventory_value,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'reconciliation_issues': reconciliation_issues,
        'pending_orders': pending_orders,
        'approval_pending_count': approval_pending_count,
        'escalated_pending_count': escalated_pending_count,
        'today_activity_count': today_activity_count,
    }

    return render_template(
        'dashboard.html',
        stats=stats,
        recent_transactions=recent_transactions,
        low_stock_products=low_stock_products_list,
        current_stock_levels=current_stock_levels,
        recent_stock_in=recent_stock_in,
        recent_stock_out=recent_stock_out,
        chart_data=chart_data,
        recent_activity=recent_activity,
        reorder_suggestions=reorder_suggestions,
    )


@bp.route('/approvals/bulk-action', methods=['POST'])
@login_required
@roles_required('admin')
def approvals_bulk_action():
    workflow = request.form.get('workflow')
    action = request.form.get('action')
    selected_ids = request.form.getlist('selected_ids')
    if not selected_ids:
        flash('Select at least one request for bulk action.', 'warning')
        return redirect(url_for('dashboard.approvals'))

    error_messages = []
    success_count = 0
    for item_id in selected_ids:
        try:
            item_id_int = int(item_id)
        except ValueError:
            continue

        if workflow == 'stock_adjustments':
            if action == 'approve':
                approve_stock_adjustment(item_id_int, current_user.id)
            elif action == 'reject':
                reject_stock_adjustment(item_id_int, current_user.id, reason='Bulk action')
            else:
                continue
        elif workflow == 'purchase_orders':
            if action == 'approve':
                approve_purchase_order(item_id_int, current_user.id)
            elif action == 'reject':
                reject_purchase_order(item_id_int, current_user.id, reason='Bulk action')
            else:
                continue
        elif workflow == 'returns':
            if action == 'approve':
                approve_return(item_id_int, current_user.id)
            elif action == 'reject':
                reject_return(item_id_int, current_user.id, reason='Bulk action')
            else:
                continue
        elif workflow == 'stock_transfers':
            if action == 'approve':
                approve_stock_transfer(item_id_int, current_user.id)
            elif action == 'reject':
                reject_stock_transfer(item_id_int, current_user.id, reason='Bulk action')
            else:
                continue
        success_count += 1

    try:
        db.session.commit()
        flash(f'Bulk {action} completed for {success_count} items.', 'success')
    except Exception:
        db.session.rollback()
        flash('Bulk action failed for one or more items.', 'danger')

    return redirect(url_for('dashboard.approvals'))


def _normalize_boundary(boundary, sample_date):
    if sample_date is None:
        return boundary
    if sample_date.tzinfo is None:
        return boundary.replace(tzinfo=None)
    return boundary.astimezone(timezone.utc)


@bp.route('/approvals')
@bp.route('/dashboard/approvals')
@login_required
@roles_required('admin', 'manager')
def approvals():
    pending_adjustments = StockAdjustment.query.filter_by(status='pending').order_by(StockAdjustment.created_at.desc()).all()
    pending_transfers = StockTransfer.query.filter_by(status='pending').order_by(StockTransfer.created_at.desc()).all()
    pending_purchase_orders = PurchaseOrder.query.filter_by(status='pending').order_by(PurchaseOrder.created_at.desc()).all()
    pending_returns = ReturnOrder.query.filter_by(status='pending').order_by(ReturnOrder.created_at.desc()).all()
    sla_boundary = utc_now() - timedelta(hours=48)

    for item_list in (pending_adjustments, pending_transfers, pending_purchase_orders, pending_returns):
        for item in item_list:
            if hasattr(item, 'created_at') and item.created_at is not None:
                boundary = _normalize_boundary(sla_boundary, item.created_at)
                item.escalated = item.created_at < boundary
            else:
                item.escalated = False

    return render_template(
        'dashboard/approvals.html',
        pending_adjustments=pending_adjustments,
        pending_transfers=pending_transfers,
        pending_purchase_orders=pending_purchase_orders,
        pending_returns=pending_returns,
        sla_boundary=sla_boundary,
    )
    
