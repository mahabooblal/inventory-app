from datetime import datetime

from app.models.audit_log import log_audit_event
from app.repositories.inventory_repository import InventoryRepository


class InventoryService:
    def __init__(self, repository=None):
        self.repository = repository or InventoryRepository()

    def list_stock_levels(self, user, req, filters=None, search=None, sort_by='product_name', sort_order='asc', page=1, per_page=20):
        filters = self._normalize_date_filters(filters)
        results, total = self.repository.list_stock_levels(
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )
        log_audit_event(user, req, 'INVENTORY_VIEWED', 'inventory_levels', 'success')
        return results, total

    def list_stock_movements(self, user, req, filters=None, search=None, sort_by='created_at', sort_order='desc', page=1, per_page=20):
        filters = self._normalize_date_filters(filters)
        results, total = self.repository.list_stock_movements(
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )
        log_audit_event(user, req, 'INVENTORY_VIEWED', 'inventory_movements', 'success')
        return results, total

    def list_low_stock_items(self, user, req, filters=None, search=None, sort_by='product_name', sort_order='asc', page=1, per_page=20):
        results, total = self.repository.list_low_stock_items(
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )
        log_audit_event(user, req, 'LOW_STOCK_VIEWED', 'inventory_low_stock', 'success')
        return results, total

    def list_inventory_valuation(self, user, req, filters=None, search=None, sort_by='product_name', sort_order='asc', page=1, per_page=20):
        filters = self._normalize_date_filters(filters)
        results, total = self.repository.list_inventory_valuation(
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )
        log_audit_event(user, req, 'INVENTORY_VALUATION_VIEWED', 'inventory_valuation', 'success')
        return results, total

    def _normalize_date_filters(self, filters):
        filters = filters or {}
        parsed = dict(filters)

        for date_field in ('start_date', 'end_date'):
            if date_field in filters and filters[date_field] is not None:
                try:
                    parsed[date_field] = datetime.fromisoformat(filters[date_field])
                except Exception:
                    raise ValueError(f'Invalid date format for {date_field}. Use ISO 8601 format.')
        return parsed
