from app.models.audit_log import log_audit_event
from app.repositories.supplier_repository import SupplierRepository


class SupplierService:
    def __init__(self, repository=None):
        self.repository = repository or SupplierRepository()

    def list_suppliers(self, filters, search, sort_by, sort_order, page, per_page):
        return self.repository.list_suppliers(filters, search, sort_by, sort_order, page, per_page)

    def get_supplier(self, supplier_id):
        supplier = self.repository.get_by_id(supplier_id)
        if supplier is None:
            raise ValueError('Supplier not found.')
        return supplier

    def create_supplier(self, user, payload, request_context=None):
        if not payload.get('name'):
            raise ValueError('Supplier name is required.')
        if not payload.get('email'):
            raise ValueError('Supplier email is required.')

        supplier = self.repository.create(payload)
        log_audit_event(user, request_context, 'SUPPLIER_CREATED', f'supplier:{supplier.id}', 'success')
        return supplier

    def update_supplier(self, user, supplier_id, payload, request_context=None):
        supplier = self.repository.get_by_id(supplier_id)
        if supplier is None:
            raise ValueError('Supplier not found.')
        if not payload:
            raise ValueError('At least one supplier field must be provided.')

        supplier = self.repository.update(supplier, payload)
        log_audit_event(user, request_context, 'SUPPLIER_UPDATED', f'supplier:{supplier.id}', 'success')
        return supplier

    def delete_supplier(self, user, supplier_id, request_context=None):
        supplier = self.repository.get_by_id(supplier_id)
        if supplier is None:
            raise ValueError('Supplier not found.')
        self.repository.delete(supplier)
        log_audit_event(user, request_context, 'SUPPLIER_DELETED', f'supplier:{supplier.id}', 'success')

    def list_products(self, supplier_id, filters, search, sort_by, sort_order, page, per_page):
        supplier = self.repository.get_by_id(supplier_id)
        if supplier is None:
            raise ValueError('Supplier not found.')
        return self.repository.list_products(supplier_id, filters, search, sort_by, sort_order, page, per_page)

    def list_purchase_orders(self, supplier_id, filters, search, sort_by, sort_order, page, per_page):
        supplier = self.repository.get_by_id(supplier_id)
        if supplier is None:
            raise ValueError('Supplier not found.')
        return self.repository.list_purchase_orders(supplier_id, filters, search, sort_by, sort_order, page, per_page)
