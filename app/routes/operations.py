from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required, current_user

from app.models import Product
from app.services.analytics_service import executive_kpis, expiring_batches, supplier_performance
from app.services.dashboard_service import get_reorder_suggestions
from app.services.reconciliation_service import (
    report_reconciliation,
    bootstrap_missing_warehouse_balances,
    reconcile_products_with_default_warehouse,
)
from app.utils.permissions import roles_required

bp = Blueprint('operations', __name__, url_prefix='/operations')


@bp.route('/reorder')
@login_required
@roles_required('admin', 'manager')
def reorder_center():
    suggestions = get_reorder_suggestions(limit=50)
    return render_template('operations/reorder.html', title='Reorder Center', suggestions=suggestions)


@bp.route('/analytics')
@login_required
@roles_required('admin', 'manager')
def analytics():
    return render_template(
        'operations/analytics.html',
        title='Executive Analytics',
        kpis=executive_kpis(),
        suppliers=supplier_performance(),
    )


@bp.route('/expiry')
@login_required
@roles_required('admin', 'manager')
def expiry_alerts():
    batches = expiring_batches()
    return render_template('operations/expiry.html', title='Expiry Alerts', batches=batches)


@bp.route('/reconciliation')
@login_required
@roles_required('admin', 'manager')
def reconciliation():
    only_mismatch = request.args.get('only_mismatch', '1') != '0'
    statuses = report_reconciliation(only_mismatch=only_mismatch)
    total_products = Product.query.count()
    try:
        pending_balances = bootstrap_missing_warehouse_balances(user_id=current_user.id, dry_run=True)
    except ValueError:
        pending_balances = []

    if request.args.get('download') == 'csv':
        from io import StringIO
        import csv

        fieldnames = [
            'product_id',
            'product_sku',
            'product_name',
            'product_quantity',
            'warehouse_total',
            'ledger_net',
            'difference_warehouse',
            'difference_ledger',
            'warehouse_mismatch',
            'ledger_mismatch',
        ]
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for status in statuses:
            writer.writerow({k: status[k] for k in fieldnames})

        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename="reconciliation_report.csv"'
        return response

    mismatch_count = sum(1 for status in statuses if status['warehouse_mismatch'] or status['ledger_mismatch'])
    warehouse_mismatch_count = sum(1 for status in statuses if status['warehouse_mismatch'])
    ledger_mismatch_count = sum(1 for status in statuses if status['ledger_mismatch'])

    return render_template(
        'operations/reconciliation.html',
        title='Reconciliation Dashboard',
        statuses=statuses,
        only_mismatch=only_mismatch,
        total_products=total_products,
        mismatch_count=mismatch_count,
        warehouse_mismatch_count=warehouse_mismatch_count,
        ledger_mismatch_count=ledger_mismatch_count,
        pending_balances=len(pending_balances),
    )


@bp.route('/reconciliation/bootstrap', methods=['POST'])
@login_required
@roles_required('admin', 'manager')
def reconciliation_bootstrap():
    try:
        actions = reconcile_products_with_default_warehouse(user_id=current_user.id, dry_run=False)
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('operations.reconciliation'))

    if actions:
        flash(f'Bootstrapped {len(actions)} missing warehouse balances.', 'success')
    else:
        flash('No missing warehouse balances were found.', 'info')
    return redirect(url_for('operations.reconciliation'))
