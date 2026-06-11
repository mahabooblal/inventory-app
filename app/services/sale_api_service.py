from decimal import Decimal

from app.models.audit_log import log_audit_event
from app.repositories.sale_repository import SaleRepository
from app.services.inventory_service import record_sale


class SaleAPIService:
    def __init__(self, repository=None):
        self.repository = repository or SaleRepository()

    def list_sales(self, *, filters=None, search=None, sort_by=None, sort_order=None, page=1, per_page=20):
        return self.repository.list_sales(
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )

    def get_sale(self, sale_id):
        return self.repository.get_by_id(sale_id)

    def create_sale(self, user, payload, request_context=None):
        if not isinstance(payload, dict):
            raise ValueError('Request payload must be a JSON object.')

        product_id = payload.get('product_id')
        quantity = payload.get('quantity')
        selling_price = payload.get('selling_price')
        customer_id = payload.get('customer_id')
        destination_details = payload.get('destination_details')

        if product_id is None or quantity is None or selling_price is None:
            raise ValueError('product_id, quantity, and selling_price are required.')

        try:
            product_id = int(product_id)
            quantity = int(quantity)
            selling_price = Decimal(str(selling_price))
        except (TypeError, ValueError):
            raise ValueError('Invalid payload values for sale.')

        if product_id <= 0 or quantity <= 0 or selling_price < 0:
            raise ValueError('product_id and quantity must be positive and selling_price cannot be negative.')

        sale = record_sale(
            product_id=product_id,
            quantity=quantity,
            selling_price=selling_price,
            user_id=user.get('user_id') or user.get('id'),
            customer_id=customer_id or None,
            destination_details=destination_details,
            commit=True,
        )

        log_audit_event(user, request_context, 'SALE_CREATED', f'sale:{sale.id}', 'success')
        return sale


SaleService = SaleAPIService
