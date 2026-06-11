from datetime import timedelta

from sqlalchemy import func

from app import db
from app.models import ActivityLog, Category, Product, Sale
from app.utils.datetime import utc_now


def _month_key(value):
    return value.strftime('%Y-%m') if hasattr(value, 'strftime') else str(value)[:7]


def get_monthly_sales_data(months=12):
    today = utc_now().date().replace(day=1)
    month_starts = []
    year = today.year
    month = today.month
    for _ in range(months):
        month_starts.append(today.replace(year=year, month=month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    month_starts.reverse()
    cutoff = month_starts[0]

    dialect = db.engine.dialect.name
    if dialect == 'postgresql':
        month_expr = func.date_trunc('month', Sale.sale_date)
    else:
        month_expr = func.strftime('%Y-%m', Sale.sale_date)

    rows = (
        db.session.query(month_expr.label('month'), func.coalesce(func.sum(Sale.total_amount), 0).label('total'))
        .filter(Sale.sale_date >= cutoff)
        .group_by(month_expr)
        .all()
    )
    totals = {_month_key(row.month): float(row.total or 0) for row in rows}
    labels = [start.strftime('%b %Y') for start in month_starts]
    values = [totals.get(start.strftime('%Y-%m'), 0.0) for start in month_starts]
    return labels, values


def get_inventory_status():
    in_stock = Product.query.filter(Product.quantity > Product.low_stock_limit).count()
    low_stock = Product.query.filter(Product.quantity <= Product.low_stock_limit, Product.quantity > 0).count()
    out_stock = Product.query.filter(Product.quantity == 0).count()
    return ['In Stock', 'Low Stock', 'Out of Stock'], [in_stock, low_stock, out_stock]


def get_top_selling_products(limit=5):
    rows = (
        db.session.query(Product.name, func.coalesce(func.sum(Sale.quantity), 0).label('qty'))
        .join(Sale, Sale.product_id == Product.id)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(Sale.quantity).desc())
        .limit(limit)
        .all()
    )
    return [row.name for row in rows], [int(row.qty or 0) for row in rows]


def get_category_distribution():
    rows = (
        db.session.query(Category.name, func.count(Product.id).label('count'))
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id, Category.name)
        .order_by(Category.name)
        .all()
    )
    return [row.name for row in rows], [int(row.count or 0) for row in rows]


def get_recent_activity(limit=10):
    return ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(limit).all()


def get_reorder_suggestions(lead_time_days=14, lookback_days=30, limit=10):
    cutoff = utc_now() - timedelta(days=lookback_days)
    rows = (
        db.session.query(Product, func.coalesce(func.sum(Sale.quantity), 0).label('total_sold'))
        .join(Sale, Sale.product_id == Product.id)
        .filter(Sale.sale_date >= cutoff)
        .group_by(Product.id)
        .all()
    )
    suggestions = []
    for product, total_sold in rows:
        avg_daily_sales = float(total_sold or 0) / lookback_days
        if avg_daily_sales <= 0:
            continue
        days_remaining = float(product.quantity) / avg_daily_sales
        if days_remaining <= lead_time_days:
            suggestions.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'quantity': product.quantity,
                'avg_daily_sales': avg_daily_sales,
                'days_remaining': days_remaining,
                'reorder_qty': max(0, round(avg_daily_sales * lead_time_days * 2) - product.quantity),
            })
    suggestions.sort(key=lambda item: item['days_remaining'])
    return suggestions[:limit]
