from sqlalchemy import asc, desc, or_

from app import db
from app.models import Customer, Product, Sale


class SaleRepository:
    SORT_FIELDS = {
        'id': Sale.id,
        'product_id': Sale.product_id,
        'customer_id': Sale.customer_id,
        'quantity': Sale.quantity,
        'selling_price': Sale.selling_price,
        'sale_date': Sale.sale_date,
        'created_by': Sale.created_by,
    }

    def list_sales(self, filters=None, search=None, sort_by=None, sort_order='asc', page=1, per_page=20):
        filters = filters or {}
        query = db.session.query(Sale).outerjoin(Product).outerjoin(Customer)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    Product.name.ilike(search_pattern),
                    Customer.name.ilike(search_pattern),
                    Sale.destination_details.ilike(search_pattern),
                )
            )

        if filters.get('product_id'):
            query = query.filter(Sale.product_id == filters['product_id'])

        if filters.get('customer_id'):
            query = query.filter(Sale.customer_id == filters['customer_id'])

        total = query.count()
        sort_column = self.SORT_FIELDS.get(sort_by, Sale.sale_date)
        order_by = asc(sort_column) if sort_order == 'asc' else desc(sort_column)
        sales = query.order_by(order_by).offset((page - 1) * per_page).limit(per_page).all()
        return sales, total

    def get_by_id(self, sale_id):
        return db.session.get(Sale, sale_id)
