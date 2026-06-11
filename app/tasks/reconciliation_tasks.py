"""Reconciliation background tasks."""

from app.tasks.runner import register_task


@register_task('reconcile_inventory_with_purchases', max_retries=2)
def reconcile_inventory_with_purchases_task():
    """Reconcile inventory levels with purchase orders."""
    from app import db
    from app.models import Stock, PurchaseOrder, PurchaseOrderItem

    orders = db.session.query(PurchaseOrder).filter(
        PurchaseOrder.status.in_(['ordered', 'partial'])
    ).all()
    discrepancies = []

    for order in orders:
        for item in order.items:
            stock = db.session.query(Stock).filter(Stock.product_id == item.product_id).first()
            if stock and item.quantity_received != item.quantity_ordered:
                discrepancies.append({
                    'order_id': order.id,
                    'product_id': item.product_id,
                    'ordered': item.quantity_ordered,
                    'received': item.quantity_received,
                })

    return {'orders_checked': len(orders), 'discrepancies': discrepancies}


@register_task('reconcile_backup_records', max_retries=2)
def reconcile_backup_records_task():
    """Reconcile backup records with filesystem."""
    from app.services.backup_service import BackupService

    result = BackupService.reconcile_backups()
    return {
        'total_records': result.get('total_records', 0),
        'missing_files': result.get('missing_files', []),
        'orphaned_files': result.get('orphaned_files', []),
    }


@register_task('check_data_consistency', max_retries=2)
def check_data_consistency_task():
    """Check overall data consistency across models."""
    from app import db
    from app.models import Sale, Invoice, Stock, Product

    issues = []

    # Check for orphaned sales
    orphaned_sales = db.session.query(Sale).filter(
        ~db.exists().where(Product.id == Sale.product_id)
    ).count()
    if orphaned_sales > 0:
        issues.append({'type': 'orphaned_sales', 'count': orphaned_sales})

    # Check for negative stock
    negative_stock = db.session.query(Stock).filter(Stock.quantity < 0).count()
    if negative_stock > 0:
        issues.append({'type': 'negative_stock', 'count': negative_stock})

    # Check for unpaid invoices with zero balance
    zero_balance_unpaid = db.session.query(Invoice).filter(
        (Invoice.status != 'paid') & (Invoice.balance_due == 0)
    ).count()
    if zero_balance_unpaid > 0:
        issues.append({'type': 'zero_balance_unpaid', 'count': zero_balance_unpaid})

    return {'data_consistency_issues': issues, 'total_issues': len(issues)}
