from app.models.audit_log import log_audit_event
from app.repositories.warehouse_repository import WarehouseRepository


class WarehouseService:
    def __init__(self, repository=None):
        self.repository = repository or WarehouseRepository()

    def list_warehouses(self, filters, search, sort_by, sort_order, page, per_page):
        return self.repository.list_warehouses(filters, search, sort_by, sort_order, page, per_page)

    def get_warehouse(self, warehouse_id):
        warehouse = self.repository.get_by_id(warehouse_id)
        if warehouse is None:
            raise ValueError('Warehouse not found.')
        return warehouse

    def create_warehouse(self, user, payload, request_context=None):
        if not payload.get('name'):
            raise ValueError('Warehouse name is required.')
        if not payload.get('code'):
            raise ValueError('Warehouse code is required.')

        warehouse = self.repository.create(payload)
        log_audit_event(user, request_context, 'WAREHOUSE_CREATED', f'warehouse:{warehouse.id}', 'success')
        return warehouse

    def update_warehouse(self, user, warehouse_id, payload, request_context=None):
        warehouse = self.repository.get_by_id(warehouse_id)
        if warehouse is None:
            raise ValueError('Warehouse not found.')
        if not payload.get('name') and not payload.get('code') and 'address' not in payload and 'is_active' not in payload:
            raise ValueError('At least one warehouse field must be provided.')

        warehouse = self.repository.update(warehouse, payload)
        log_audit_event(user, request_context, 'WAREHOUSE_UPDATED', f'warehouse:{warehouse.id}', 'success')
        return warehouse

    def delete_warehouse(self, user, warehouse_id, request_context=None):
        warehouse = self.repository.get_by_id(warehouse_id)
        if warehouse is None:
            raise ValueError('Warehouse not found.')
        self.repository.delete(warehouse)
        log_audit_event(user, request_context, 'WAREHOUSE_DELETED', f'warehouse:{warehouse.id}', 'success')

    def list_inventory(self, warehouse_id, filters, search, sort_by, sort_order, page, per_page):
        warehouse = self.repository.get_by_id(warehouse_id)
        if warehouse is None:
            raise ValueError('Warehouse not found.')
        return self.repository.list_inventory(warehouse_id, filters, search, sort_by, sort_order, page, per_page)

    def list_movements(self, warehouse_id, filters, search, sort_by, sort_order, page, per_page):
        warehouse = self.repository.get_by_id(warehouse_id)
        if warehouse is None:
            raise ValueError('Warehouse not found.')
        return self.repository.list_movements(warehouse_id, filters, search, sort_by, sort_order, page, per_page)
