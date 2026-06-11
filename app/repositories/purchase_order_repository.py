from decimal import Decimal

from sqlalchemy import asc, desc, or_

from app import db
from app.models import Product, PurchaseOrder, PurchaseOrderItem, Supplier
from app.services.purchase_order_service import next_po_number


class PurchaseOrderRepository:
    SORT_FIELDS = {
        'id': PurchaseOrder.id,
        'po_number': PurchaseOrder.po_number,
        'status': PurchaseOrder.status,
        'expected_date': PurchaseOrder.expected_date,
        'created_at': PurchaseOrder.created_at,
    }

    def list_purchase_orders(self, filters=None, search=None, sort_by=None, sort_order='asc', page=1, per_page=20):
        filters = filters or {}
        query = db.session.query(PurchaseOrder).outerjoin(Supplier)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    PurchaseOrder.po_number.ilike(search_pattern),
                    PurchaseOrder.status.ilike(search_pattern),
                    Supplier.name.ilike(search_pattern),
                )
            )

        if filters.get('supplier_id'):
            query = query.filter(PurchaseOrder.supplier_id == filters['supplier_id'])

        if filters.get('status'):
            query = query.filter(PurchaseOrder.status == filters['status'])

        if filters.get('po_number'):
            query = query.filter(PurchaseOrder.po_number == filters['po_number'])

        total = query.count()
        sort_column = self.SORT_FIELDS.get(sort_by, PurchaseOrder.created_at)
        order_by = asc(sort_column) if sort_order == 'asc' else desc(sort_column)
        purchase_orders = query.order_by(order_by).offset((page - 1) * per_page).limit(per_page).all()
        return purchase_orders, total

    def get_by_id(self, purchase_order_id):
        return db.session.get(PurchaseOrder, purchase_order_id)

    def create(self, supplier_id, created_by, items, expected_date=None, notes=None):
        supplier = db.session.get(Supplier, supplier_id)
        if supplier is None:
            raise ValueError('Supplier not found')

        purchase_order = PurchaseOrder(
            po_number=next_po_number(),
            supplier_id=supplier_id,
            status='draft',
            expected_date=expected_date,
            notes=notes,
            created_by=created_by,
        )
        db.session.add(purchase_order)
        db.session.flush()

        self._attach_items(purchase_order, items)
        db.session.commit()
        return purchase_order

    def update(self, purchase_order, data):
        if data.get('supplier_id') is not None:
            supplier = db.session.get(Supplier, data['supplier_id'])
            if supplier is None:
                raise ValueError('Supplier not found')
            purchase_order.supplier_id = data['supplier_id']

        if data.get('expected_date') is not None:
            purchase_order.expected_date = data['expected_date']

        if data.get('notes') is not None:
            purchase_order.notes = data['notes']

        if data.get('status') is not None:
            purchase_order.status = data['status']

        if data.get('cancellation_reason') is not None:
            purchase_order.cancellation_reason = data['cancellation_reason']

        if data.get('items') is not None:
            purchase_order.items[:] = []
            self._attach_items(purchase_order, data['items'])

        db.session.add(purchase_order)
        db.session.commit()
        return purchase_order

    def delete(self, purchase_order):
        db.session.delete(purchase_order)
        db.session.commit()

    def _attach_items(self, purchase_order, items):
        for item in items:
            product = db.session.get(Product, item['product_id'])
            if product is None:
                raise ValueError(f"Product not found: {item['product_id']}")

            purchase_order.items.append(
                PurchaseOrderItem(
                    purchase_order_id=purchase_order.id,
                    product_id=item['product_id'],
                    quantity_ordered=item['quantity_ordered'],
                    quantity_received=item.get('quantity_received', 0),
                    unit_cost=Decimal(item['unit_cost']),
                )
            )

        db.session.flush()
