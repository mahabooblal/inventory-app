from sqlalchemy import asc, desc, or_

from app import db
from app.models import Customer, Product, ReturnOrder, Supplier


class ReturnRepository:
    SORT_FIELDS = {
        'id': ReturnOrder.id,
        'return_number': ReturnOrder.return_number,
        'return_type': ReturnOrder.return_type,
        'status': ReturnOrder.status,
        'quantity': ReturnOrder.quantity,
        'created_at': ReturnOrder.created_at,
    }

    def list_returns(self, filters=None, search=None, sort_by=None, sort_order='asc', page=1, per_page=20):
        filters = filters or {}
        query = db.session.query(ReturnOrder).outerjoin(Product).outerjoin(Customer).outerjoin(Supplier)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    ReturnOrder.return_number.ilike(search_pattern),
                    ReturnOrder.status.ilike(search_pattern),
                    Product.name.ilike(search_pattern),
                )
            )

        if filters.get('return_type'):
            query = query.filter(ReturnOrder.return_type == filters['return_type'])

        if filters.get('status'):
            query = query.filter(ReturnOrder.status == filters['status'])

        if filters.get('product_id'):
            query = query.filter(ReturnOrder.product_id == filters['product_id'])

        if filters.get('customer_id'):
            query = query.filter(ReturnOrder.customer_id == filters['customer_id'])

        if filters.get('supplier_id'):
            query = query.filter(ReturnOrder.supplier_id == filters['supplier_id'])

        total = query.count()
        sort_column = self.SORT_FIELDS.get(sort_by, ReturnOrder.created_at)
        order_by = asc(sort_column) if sort_order == 'asc' else desc(sort_column)
        returns = query.order_by(order_by).offset((page - 1) * per_page).limit(per_page).all()
        return returns, total

    def get_by_id(self, return_order_id):
        return db.session.get(ReturnOrder, return_order_id)
