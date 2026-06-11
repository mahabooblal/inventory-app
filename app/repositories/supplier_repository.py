from sqlalchemy import asc, desc, or_

from app import db
from app.models import Product, PurchaseOrder, Supplier


class SupplierRepository:
    SORT_FIELDS = {
        'id': Supplier.id,
        'name': Supplier.name,
        'email': Supplier.email,
        'created_at': Supplier.created_at,
    }

    PRODUCT_SORT_FIELDS = {
        'name': Product.name,
        'sku': Product.sku,
        'barcode': Product.barcode,
    }

    ORDER_SORT_FIELDS = {
        'created_at': PurchaseOrder.created_at,
        'status': PurchaseOrder.status,
        'po_number': PurchaseOrder.po_number,
    }

    def list_suppliers(self, filters=None, search=None, sort_by='name', sort_order='asc', page=1, per_page=20):
        filters = filters or {}
        query = db.session.query(Supplier)

        if search:
            pattern = f'%{search}%'
            query = query.filter(
                or_(
                    Supplier.name.ilike(pattern),
                    Supplier.email.ilike(pattern),
                    Supplier.phone.ilike(pattern),
                )
            )

        if 'is_active' in filters:
            value = filters['is_active']
            if isinstance(value, str):
                value = value.lower() in ('1', 'true', 'yes')
            query = query.filter(Supplier.is_active.is_(bool(value)))

        total = query.count()
        sort_column = self.SORT_FIELDS.get(sort_by, Supplier.name)
        order_fn = asc if sort_order == 'asc' else desc
        query = query.order_by(order_fn(sort_column))
        suppliers = query.offset((page - 1) * per_page).limit(per_page).all()
        return suppliers, total

    def get_by_id(self, supplier_id):
        return db.session.get(Supplier, supplier_id)

    def create(self, data):
        supplier = Supplier(
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            is_active=data.get('is_active', True),
        )
        db.session.add(supplier)
        db.session.commit()
        return supplier

    def update(self, supplier, data):
        if 'name' in data:
            supplier.name = data['name']
        if 'email' in data:
            supplier.email = data['email']
        if 'phone' in data:
            supplier.phone = data['phone']
        if 'address' in data:
            supplier.address = data['address']
        if 'is_active' in data:
            supplier.is_active = bool(data['is_active'])

        db.session.add(supplier)
        db.session.commit()
        return supplier

    def delete(self, supplier):
        db.session.delete(supplier)
        db.session.commit()

    def list_purchase_orders(self, supplier_id, filters=None, search=None, sort_by='created_at', sort_order='desc', page=1, per_page=20):
        filters = filters or {}
        query = db.session.query(PurchaseOrder).filter(PurchaseOrder.supplier_id == supplier_id)

        if search:
            pattern = f'%{search}%'
            query = query.filter(
                or_(
                    PurchaseOrder.po_number.ilike(pattern),
                    PurchaseOrder.status.ilike(pattern),
                )
            )

        if 'status' in filters:
            query = query.filter(PurchaseOrder.status == filters['status'])

        total = query.count()
        sort_column = self.ORDER_SORT_FIELDS.get(sort_by, PurchaseOrder.created_at)
        order_fn = asc if sort_order == 'asc' else desc
        query = query.order_by(order_fn(sort_column))
        orders = query.offset((page - 1) * per_page).limit(per_page).all()
        return orders, total

    def list_products(self, supplier_id, filters=None, search=None, sort_by='name', sort_order='asc', page=1, per_page=20):
        filters = filters or {}
        query = db.session.query(Product).filter(Product.supplier_id == supplier_id)

        if search:
            pattern = f'%{search}%'
            query = query.filter(
                or_(
                    Product.name.ilike(pattern),
                    Product.sku.ilike(pattern),
                    Product.barcode.ilike(pattern),
                )
            )

        if 'category_id' in filters:
            query = query.filter(Product.category_id == filters['category_id'])

        total = query.count()
        sort_column = self.PRODUCT_SORT_FIELDS.get(sort_by, Product.name)
        order_fn = asc if sort_order == 'asc' else desc
        query = query.order_by(order_fn(sort_column))
        products = query.offset((page - 1) * per_page).limit(per_page).all()
        return products, total
