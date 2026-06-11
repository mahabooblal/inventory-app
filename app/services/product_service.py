from app.api.base import ValidationError
from app.models.audit_log import log_audit_event
from app.repositories.product_repository import ProductRepository


class ProductService:
    def __init__(self, repository=None):
        self.repository = repository or ProductRepository()

    def list_products(self, filters=None, search=None, sort_by='name', sort_order='asc', page=1, per_page=20):
        return self.repository.list_products(
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )

    def get_product(self, product_id):
        product = self.repository.get_by_id(product_id)
        if not product:
            raise ValueError('Product not found.')
        return product

    def create_product(self, user, payload, req=None):
        if not payload.get('sku'):
            raise ValidationError('SKU is required.', errors={'sku': 'SKU is required'})
        if self.repository.exists_sku(payload['sku']):
            raise ValidationError('Product SKU already exists.', errors={'sku': 'SKU must be unique'})

        product = self.repository.create(payload)
        log_audit_event(user, req, 'PRODUCT_CREATED', f'product:{product.id}', 'success')
        return product

    def update_product(self, user, product_id, payload, req=None):
        product = self.repository.get_by_id(product_id)
        if not product:
            raise ValueError('Product not found.')

        if 'sku' in payload and self.repository.exists_sku(payload['sku'], exclude_id=product_id):
            raise ValidationError('Product SKU already exists.', errors={'sku': 'SKU must be unique'})

        product = self.repository.update(product, payload)
        log_audit_event(user, req, 'PRODUCT_UPDATED', f'product:{product.id}', 'success')
        return product

    def delete_product(self, user, product_id, req=None):
        product = self.repository.get_by_id(product_id)
        if not product:
            raise ValueError('Product not found.')

        self.repository.delete(product)
        log_audit_event(user, req, 'PRODUCT_DELETED', f'product:{product.id}', 'success')
        return True
