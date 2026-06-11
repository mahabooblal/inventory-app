from sqlalchemy import asc, desc, or_

from app import db
from app.models import Product


class ProductRepository:
    SORT_FIELDS = {
        'id': Product.id,
        'name': Product.name,
        'sku': Product.sku,
        'barcode': Product.barcode,
        'price': Product.price,
        'quantity': Product.quantity,
        'created_at': Product.created_at,
    }

    def list_products(self, filters=None, search=None, sort_by='name', sort_order='asc', page=1, per_page=20):
        filters = filters or {}
        query = db.session.query(Product)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    Product.name.ilike(search_pattern),
                    Product.sku.ilike(search_pattern),
                    Product.barcode.ilike(search_pattern),
                    Product.description.ilike(search_pattern),
                )
            )

        if filters.get('category_id'):
            query = query.filter(Product.category_id == int(filters['category_id']))
        if filters.get('supplier_id'):
            query = query.filter(Product.supplier_id == int(filters['supplier_id']))
        if filters.get('is_active') is not None:
            active_value = filters['is_active'] in ('1', 'true', 'True', True)
            query = query.filter(Product.is_active == active_value)

        total = query.count()

        sort_column = self.SORT_FIELDS.get(sort_by, Product.name)
        order = desc(sort_column) if sort_order == 'desc' else asc(sort_column)
        query = query.order_by(order)

        products = query.offset((page - 1) * per_page).limit(per_page).all()
        return products, total

    def get_by_id(self, product_id):
        return db.session.get(Product, product_id)

    def exists_sku(self, sku, exclude_id=None):
        query = db.session.query(Product).filter(Product.sku == sku)
        if exclude_id:
            query = query.filter(Product.id != exclude_id)
        return db.session.query(query.exists()).scalar()

    def create(self, data):
        product = Product(
            name=data.get('name'),
            sku=data.get('sku'),
            barcode=data.get('barcode'),
            description=data.get('description'),
            image_filename=data.get('image_filename'),
            is_active=data.get('is_active', True),
            price=data.get('price', 0),
            cost_price=data.get('cost_price', 0),
            quantity=data.get('quantity', 0),
            low_stock_limit=data.get('low_stock_limit', 0),
            category_id=data.get('category_id'),
            supplier_id=data.get('supplier_id'),
        )
        db.session.add(product)
        db.session.commit()
        return product

    def update(self, product, data):
        for key in [
            'name', 'sku', 'barcode', 'description', 'image_filename', 'is_active',
            'price', 'cost_price', 'quantity', 'low_stock_limit', 'category_id', 'supplier_id',
        ]:
            if key in data:
                setattr(product, key, data[key])

        db.session.add(product)
        db.session.commit()
        return product

    def delete(self, product):
        db.session.delete(product)
        db.session.commit()
