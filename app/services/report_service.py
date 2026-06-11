from sqlalchemy import func
from app import db
from app.models import Product, Sale, StockIn
from app.utils.datetime import utc_day_bounds


def date_range(from_date, to_date):
    return utc_day_bounds(from_date, to_date)


def sales_query_between(from_date, to_date):
    start, end = date_range(from_date, to_date)
    return Sale.query.filter(Sale.sale_date.between(start, end))


def sales_between(from_date, to_date):
    return sales_query_between(from_date, to_date).order_by(Sale.sale_date.desc()).all()


def low_stock_products():
    return Product.query.filter(Product.quantity <= Product.low_stock_limit).order_by(Product.quantity.asc()).all()


def sales_total(sales):
    return sum(sale.total_amount for sale in sales)


def inventory_report():
    """Return list of products with quantities, price, cost and total values."""
    products = (
        db.session.query(
            Product.id,
            Product.name,
            Product.sku,
            Product.quantity,
            Product.price,
            Product.cost_price,
        )
        .order_by(Product.name)
        .all()
    )
    report = []
    for p in products:
        report.append({
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'quantity': p.quantity,
            'price': p.price,
            'cost_price': getattr(p, 'cost_price', 0.0),
            'total_value': p.quantity * p.price,
            'total_cost': p.quantity * getattr(p, 'cost_price', 0.0),
        })
    return report


def product_sales_between(product_id, from_date, to_date):
    return (
        sales_query_between(from_date, to_date)
        .filter(Sale.product_id == product_id)
        .order_by(Sale.sale_date.desc())
        .all()
    )


def category_sales_between(category_id, from_date, to_date):
    return (
        sales_query_between(from_date, to_date)
        .join(Product)
        .filter(Product.category_id == category_id)
        .order_by(Sale.sale_date.desc())
        .all()
    )


def customer_sales_between(customer_id, from_date, to_date):
    return (
        sales_query_between(from_date, to_date)
        .filter(Sale.customer_id == customer_id)
        .order_by(Sale.sale_date.desc())
        .all()
    )


def profit_loss_between(from_date, to_date):
    sales = sales_between(from_date, to_date)
    revenue = sum(s.total_amount for s in sales)
    cost = (
        sales_query_between(from_date, to_date)
        .join(Product)
        .with_entities(func.coalesce(func.sum(Sale.quantity * Product.cost_price), 0))
        .scalar()
        or 0
    )
    profit = revenue - cost
    return {
        'revenue': revenue,
        'cost': cost,
        'profit': profit,
        'sales': sales,
    }


def incoming_between(from_date, to_date, product_id=None):
    start, end = date_range(from_date, to_date)
    query = StockIn.query.filter(StockIn.created_at.between(start, end))
    if product_id:
        query = query.filter(StockIn.product_id == product_id)
    return query.order_by(StockIn.created_at.desc()).all()


def outgoing_between(from_date, to_date, product_id=None):
    query = sales_query_between(from_date, to_date)
    if product_id:
        query = query.filter(Sale.product_id == product_id)
    return query.order_by(Sale.sale_date.desc()).all()


def movement_summary_between(from_date, to_date, product_id=None):
    incoming = incoming_between(from_date, to_date, product_id)
    outgoing = outgoing_between(from_date, to_date, product_id)
    incoming_qty = sum(item.quantity for item in incoming)
    outgoing_qty = sum(item.quantity for item in outgoing)
    products = Product.query.order_by(Product.name).all()
    if product_id:
        products = [p for p in products if p.id == product_id]
    product_rows = []
    for product in products:
        in_qty = sum(item.quantity for item in incoming if item.product_id == product.id)
        out_qty = sum(item.quantity for item in outgoing if item.product_id == product.id)
        if in_qty or out_qty:
            product_rows.append({
                'product': product,
                'incoming': in_qty,
                'outgoing': out_qty,
                'net': in_qty - out_qty,
            })
    return {
        'incoming': incoming,
        'outgoing': outgoing,
        'incoming_qty': incoming_qty,
        'outgoing_qty': outgoing_qty,
        'net_qty': incoming_qty - outgoing_qty,
        'product_rows': product_rows,
    }
