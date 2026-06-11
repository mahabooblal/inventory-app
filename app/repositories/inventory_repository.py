from datetime import datetime
from sqlalchemy import asc, desc, func, or_

from app import db
from app.models import Product, StockMovement, Warehouse, WarehouseStock


class InventoryRepository:
    STOCK_LEVEL_SORT_FIELDS = {
        'product_name': Product.name,
        'sku': Product.sku,
        'warehouse_name': Warehouse.name,
        'quantity': WarehouseStock.quantity,
    }

    MOVEMENT_SORT_FIELDS = {
        'created_at': StockMovement.created_at,
        'product_name': Product.name,
        'quantity': StockMovement.quantity,
        'movement_type': StockMovement.movement_type,
    }

    LOW_STOCK_SORT_FIELDS = {
        'product_name': Product.name,
        'sku': Product.sku,
        'quantity': WarehouseStock.quantity,
        'low_stock_limit': Product.low_stock_limit,
    }

    VALUATION_SORT_FIELDS = {
        'product_name': Product.name,
        'sku': Product.sku,
        'warehouse_name': Warehouse.name,
        'quantity': WarehouseStock.quantity,
        'value': WarehouseStock.quantity * Product.cost_price,
    }

    def list_stock_levels(self, filters=None, search=None, sort_by='product_name', sort_order='asc', page=1, per_page=20):
        filters = filters or {}
        query = db.session.query(WarehouseStock, Product, Warehouse)
        query = query.join(Product, WarehouseStock.product).join(Warehouse, WarehouseStock.warehouse)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(Product.name.ilike(search_pattern), Product.sku.ilike(search_pattern))
            )

        if filters.get('product_id'):
            query = query.filter(WarehouseStock.product_id == int(filters['product_id']))
        if filters.get('warehouse_id'):
            query = query.filter(WarehouseStock.warehouse_id == int(filters['warehouse_id']))

        total = query.count()

        sort_column = self.STOCK_LEVEL_SORT_FIELDS.get(sort_by, Product.name)
        order = desc(sort_column) if sort_order == 'desc' else asc(sort_column)
        query = query.order_by(order)

        entries = query.offset((page - 1) * per_page).limit(per_page).all()
        results = []
        for stock, product, warehouse in entries:
            results.append({
                'product_id': product.id,
                'product_name': product.name,
                'sku': product.sku,
                'warehouse_id': warehouse.id,
                'warehouse_name': warehouse.name,
                'quantity': stock.quantity,
                'unit_cost': float(product.cost_price) if product.cost_price is not None else 0.0,
                'total_value': float(stock.quantity * product.cost_price) if product.cost_price is not None else 0.0,
            })
        return results, total

    def list_stock_movements(self, filters=None, search=None, sort_by='created_at', sort_order='desc', page=1, per_page=20):
        filters = filters or {}
        query = db.session.query(StockMovement, Product).join(Product)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(Product.name.ilike(search_pattern), Product.sku.ilike(search_pattern))
            )

        if filters.get('product_id'):
            query = query.filter(StockMovement.product_id == int(filters['product_id']))
        if filters.get('movement_type'):
            query = query.filter(StockMovement.movement_type == filters['movement_type'])
        if filters.get('start_date'):
            query = query.filter(StockMovement.created_at >= filters['start_date'])
        if filters.get('end_date'):
            query = query.filter(StockMovement.created_at <= filters['end_date'])

        total = query.count()

        sort_column = self.MOVEMENT_SORT_FIELDS.get(sort_by, StockMovement.created_at)
        order = desc(sort_column) if sort_order == 'desc' else asc(sort_column)
        query = query.order_by(order)

        entries = query.offset((page - 1) * per_page).limit(per_page).all()
        results = []
        for movement, product in entries:
            results.append({
                'id': movement.id,
                'product_id': product.id,
                'product_name': product.name,
                'sku': product.sku,
                'movement_type': movement.movement_type,
                'quantity': movement.quantity,
                'quantity_before': movement.quantity_before,
                'quantity_after': movement.quantity_after,
                'unit_cost': float(movement.unit_cost) if movement.unit_cost is not None else 0.0,
                'reference_type': movement.reference_type,
                'reference_id': movement.reference_id,
                'note': movement.note,
                'created_at': movement.created_at.isoformat() if movement.created_at else None,
            })
        return results, total

    def list_low_stock_items(self, filters=None, search=None, sort_by='product_name', sort_order='asc', page=1, per_page=20):
        filters = filters or {}
        if filters.get('warehouse_id'):
            query = db.session.query(WarehouseStock, Product, Warehouse)
            query = query.join(Product, WarehouseStock.product).join(Warehouse, WarehouseStock.warehouse)
            query = query.filter(WarehouseStock.warehouse_id == int(filters['warehouse_id']))
            query = query.filter(WarehouseStock.quantity <= Product.low_stock_limit)
        else:
            query = db.session.query(Product)
            query = query.filter(Product.quantity <= Product.low_stock_limit)

        if search:
            search_pattern = f'%{search}%'
            if filters.get('warehouse_id'):
                query = query.filter(or_(Product.name.ilike(search_pattern), Product.sku.ilike(search_pattern)))
            else:
                query = query.filter(or_(Product.name.ilike(search_pattern), Product.sku.ilike(search_pattern)))

        total = query.count()

        sort_column = self.LOW_STOCK_SORT_FIELDS.get(sort_by, Product.name)
        order = desc(sort_column) if sort_order == 'desc' else asc(sort_column)
        query = query.order_by(order)

        entries = query.offset((page - 1) * per_page).limit(per_page).all()
        results = []
        if filters.get('warehouse_id'):
            for stock, product, warehouse in entries:
                results.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'sku': product.sku,
                    'quantity': stock.quantity,
                    'low_stock_limit': product.low_stock_limit,
                    'is_low_stock': stock.quantity <= product.low_stock_limit,
                    'warehouse_id': warehouse.id,
                    'warehouse_name': warehouse.name,
                })
        else:
            for product in entries:
                results.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'sku': product.sku,
                    'quantity': product.quantity,
                    'low_stock_limit': product.low_stock_limit,
                    'is_low_stock': product.quantity <= product.low_stock_limit,
                    'warehouse_id': None,
                    'warehouse_name': None,
                })
        return results, total

    def list_inventory_valuation(self, filters=None, search=None, sort_by='product_name', sort_order='asc', page=1, per_page=20):
        filters = filters or {}
        query = db.session.query(WarehouseStock, Product, Warehouse)
        query = query.join(Product, WarehouseStock.product).join(Warehouse, WarehouseStock.warehouse)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(or_(Product.name.ilike(search_pattern), Product.sku.ilike(search_pattern)))

        if filters.get('warehouse_id'):
            query = query.filter(WarehouseStock.warehouse_id == int(filters['warehouse_id']))
        if filters.get('product_id'):
            query = query.filter(WarehouseStock.product_id == int(filters['product_id']))
        if filters.get('start_date'):
            query = query.filter(WarehouseStock.updated_at >= filters['start_date'])
        if filters.get('end_date'):
            query = query.filter(WarehouseStock.updated_at <= filters['end_date'])
        if filters.get('start_date'):
            query = query.filter(WarehouseStock.updated_at >= filters['start_date'])
        if filters.get('end_date'):
            query = query.filter(WarehouseStock.updated_at <= filters['end_date'])

        total = query.count()

        sort_column = self.VALUATION_SORT_FIELDS.get(sort_by, Product.name)
        order = desc(sort_column) if sort_order == 'desc' else asc(sort_column)
        query = query.order_by(order)

        entries = query.offset((page - 1) * per_page).limit(per_page).all()
        results = []
        for stock, product, warehouse in entries:
            value = float(stock.quantity * product.cost_price) if product.cost_price is not None else 0.0
            results.append({
                'product_id': product.id,
                'product_name': product.name,
                'sku': product.sku,
                'warehouse_id': warehouse.id,
                'warehouse_name': warehouse.name,
                'quantity': stock.quantity,
                'unit_cost': float(product.cost_price) if product.cost_price is not None else 0.0,
                'value': value,
            })
        return results, total
