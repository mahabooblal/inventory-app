"""Inventory-related background tasks."""

from app.tasks.runner import register_task


@register_task('reconcile_inventory', max_retries=2)
def reconcile_inventory_task():
    """Perform full inventory reconciliation."""
    from app.services.inventory_service import reconcile_inventory

    result = reconcile_inventory()
    return {
        'reconciled': result.get('reconciled', 0),
        'discrepancies': result.get('discrepancies', []),
    }


@register_task('check_stock_levels', max_retries=1)
def check_stock_levels_task():
    """Check stock levels and identify low stock items."""
    from app import db
    from app.models import Stock

    low_stock_items = db.session.query(Stock).filter(Stock.quantity < Stock.reorder_point).all()
    return {
        'low_stock_count': len(low_stock_items),
        'items': [{'product_id': s.product_id, 'quantity': s.quantity} for s in low_stock_items],
    }


@register_task('validate_stock_consistency', max_retries=2)
def validate_stock_consistency_task():
    """Validate stock consistency across warehouses."""
    from app import db
    from app.models import Stock

    stocks = db.session.query(Stock).all()
    inconsistencies = []
    for stock in stocks:
        if stock.quantity < 0:
            inconsistencies.append({'stock_id': stock.id, 'issue': 'negative_quantity'})
    return {
        'total_stocks': len(stocks),
        'inconsistencies': inconsistencies,
    }
