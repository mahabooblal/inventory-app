from datetime import timedelta

from sqlalchemy import func

from app import db
from app.models import Product, PurchaseOrder, ReturnOrder, Sale, StockIn, Supplier
from app.utils.datetime import utc_now


def executive_kpis(lookback_days=30):
    cutoff = utc_now() - timedelta(days=lookback_days)
    revenue = db.session.query(func.coalesce(func.sum(Sale.total_amount), 0)).filter(Sale.sale_date >= cutoff).scalar() or 0
    units_sold = db.session.query(func.coalesce(func.sum(Sale.quantity), 0)).filter(Sale.sale_date >= cutoff).scalar() or 0
    inventory_value = db.session.query(func.coalesce(func.sum(Product.quantity * Product.cost_price), 0)).scalar() or 0
    low_stock = Product.query.filter(Product.quantity <= Product.low_stock_limit).count()
    returns = ReturnOrder.query.filter(ReturnOrder.created_at >= cutoff).count()
    open_pos = PurchaseOrder.query.filter(PurchaseOrder.status.in_(['ordered', 'partially_received'])).count()
    dead_stock_cutoff = utc_now() - timedelta(days=90)
    sold_product_ids = db.session.query(Sale.product_id).filter(Sale.sale_date >= dead_stock_cutoff)
    dead_stock = Product.query.filter(Product.quantity > 0, ~Product.id.in_(sold_product_ids)).count()
    return {
        'revenue': revenue,
        'units_sold': units_sold,
        'inventory_value': inventory_value,
        'low_stock': low_stock,
        'returns': returns,
        'open_pos': open_pos,
        'dead_stock': dead_stock,
    }


def supplier_performance(limit=10):
    rows = (
        db.session.query(
            Supplier.name,
            func.coalesce(func.sum(StockIn.quantity), 0).label('received_qty'),
            func.count(PurchaseOrder.id).label('po_count'),
        )
        .outerjoin(StockIn, StockIn.supplier_id == Supplier.id)
        .outerjoin(PurchaseOrder, PurchaseOrder.supplier_id == Supplier.id)
        .group_by(Supplier.id, Supplier.name)
        .order_by(func.coalesce(func.sum(StockIn.quantity), 0).desc())
        .limit(limit)
        .all()
    )
    return rows


def expiring_batches(days=30):
    cutoff = utc_now().date() + timedelta(days=days)
    return (
        StockIn.query
        .filter(StockIn.expires_on.isnot(None), StockIn.expires_on <= cutoff)
        .order_by(StockIn.expires_on.asc())
        .all()
    )
