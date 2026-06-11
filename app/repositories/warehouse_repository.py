from sqlalchemy import asc, desc, or_

from app import db
from app.models import Product, StockTransfer, Warehouse, WarehouseStock


class WarehouseRepository:
    SORT_FIELDS = {
        'id': Warehouse.id,
        'name': Warehouse.name,
        'code': Warehouse.code,
        'created_at': Warehouse.created_at,
    }

    INVENTORY_SORT_FIELDS = {
        'product_name': Product.name,
        'sku': Product.sku,
        'quantity': WarehouseStock.quantity,
    }

    MOVEMENT_SORT_FIELDS = {
        'created_at': StockTransfer.created_at,
        'product_name': Product.name,
        'quantity': StockTransfer.quantity,
        'status': StockTransfer.status,
    }

    def list_warehouses(self, filters=None, search=None, sort_by='name', sort_order='asc', page=1, per_page=20):
        filters = filters or {}
        query = db.session.query(Warehouse)

        if search:
            pattern = f'%{search}%'
            query = query.filter(
                or_(
                    Warehouse.name.ilike(pattern),
                    Warehouse.code.ilike(pattern),
                    Warehouse.address.ilike(pattern),
                )
            )

        if 'code' in filters:
            query = query.filter(Warehouse.code == filters['code'])

        if 'is_active' in filters:
            value = filters['is_active']
            if isinstance(value, str):
                value = value.lower() in ('1', 'true', 'yes')
            query = query.filter(Warehouse.is_active.is_(bool(value)))

        total = query.count()
        sort_column = self.SORT_FIELDS.get(sort_by, Warehouse.name)
        order_fn = asc if sort_order == 'asc' else desc
        query = query.order_by(order_fn(sort_column))
        warehouses = query.offset((page - 1) * per_page).limit(per_page).all()
        return warehouses, total

    def get_by_id(self, warehouse_id):
        return db.session.get(Warehouse, warehouse_id)

    def create(self, data):
        warehouse = Warehouse(
            name=data.get('name'),
            code=data.get('code'),
            address=data.get('address'),
            is_active=data.get('is_active', True),
        )
        db.session.add(warehouse)
        db.session.commit()
        return warehouse

    def update(self, warehouse, data):
        if 'name' in data:
            warehouse.name = data['name']
        if 'code' in data:
            warehouse.code = data['code']
        if 'address' in data:
            warehouse.address = data['address']
        if 'is_active' in data:
            warehouse.is_active = bool(data['is_active'])

        db.session.add(warehouse)
        db.session.commit()
        return warehouse

    def delete(self, warehouse):
        db.session.delete(warehouse)
        db.session.commit()

    def list_inventory(self, warehouse_id, filters=None, search=None, sort_by='product_name', sort_order='asc', page=1, per_page=20):
        filters = filters or {}
        query = (
            db.session.query(WarehouseStock, Product)
            .join(Product, WarehouseStock.product)
            .filter(WarehouseStock.warehouse_id == warehouse_id)
        )

        if search:
            pattern = f'%{search}%'
            query = query.filter(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))

        if 'product_id' in filters:
            query = query.filter(Product.id == filters['product_id'])

        total = query.count()
        sort_column = self.INVENTORY_SORT_FIELDS.get(sort_by, Product.name)
        order_fn = asc if sort_order == 'asc' else desc
        query = query.order_by(order_fn(sort_column))
        records = query.offset((page - 1) * per_page).limit(per_page).all()
        return records, total

    def list_movements(self, warehouse_id, filters=None, search=None, sort_by='created_at', sort_order='desc', page=1, per_page=20):
        filters = filters or {}
        query = (
            db.session.query(StockTransfer, Product)
            .join(Product, StockTransfer.product)
            .filter(
                (StockTransfer.source_warehouse_id == warehouse_id)
                | (StockTransfer.destination_warehouse_id == warehouse_id)
            )
        )

        if search:
            pattern = f'%{search}%'
            query = query.filter(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))

        if 'status' in filters:
            query = query.filter(StockTransfer.status == filters['status'])

        total = query.count()
        sort_column = self.MOVEMENT_SORT_FIELDS.get(sort_by, StockTransfer.created_at)
        order_fn = asc if sort_order == 'asc' else desc
        query = query.order_by(order_fn(sort_column))
        records = query.offset((page - 1) * per_page).limit(per_page).all()
        return records, total
