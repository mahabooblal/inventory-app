from datetime import date
from decimal import Decimal

from app import db
from app.models import Product, PurchaseOrder, PurchaseOrderItem, Supplier
from app.models.audit_log import log_audit_event
from app.services.inventory_service import add_stock
from app.repositories.purchase_order_repository import PurchaseOrderRepository
from app.utils.datetime import utc_now


class PurchaseOrderAPIService:
    def __init__(self, repository=None):
        self.repository = repository or PurchaseOrderRepository()

    def list_purchase_orders(self, *, filters=None, search=None, sort_by=None, sort_order=None, page=1, per_page=20):
        return self.repository.list_purchase_orders(
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )

    def get_purchase_order(self, purchase_order_id):
        return self.repository.get_by_id(purchase_order_id)

    def create_purchase_order(self, user, payload, request_context=None):
        supplier_id = payload.get('supplier_id')
        if supplier_id is None:
            raise ValueError('Supplier id is required.')

        items = self._normalize_items(payload.get('items'))
        expected_date = self._parse_expected_date(payload.get('expected_date'))
        notes = payload.get('notes')

        purchase_order = self.repository.create(
            supplier_id=supplier_id,
            created_by=user.get('user_id') or user.get('id'),
            items=items,
            expected_date=expected_date,
            notes=notes,
        )

        log_audit_event(user, request_context, 'PO_CREATED', f'purchase_order:{purchase_order.id}', 'success')
        return purchase_order

    def update_purchase_order(self, user, purchase_order_id, payload, request_context=None):
        purchase_order = self.repository.get_by_id(purchase_order_id)
        if purchase_order is None:
            raise ValueError('Purchase order not found')

        if not isinstance(payload, dict) or not payload:
            raise ValueError('Request payload must be a JSON object.')

        updates = {}

        if payload.get('supplier_id') is not None:
            if purchase_order.status != 'draft':
                raise ValueError('Supplier id can only be updated for draft purchase orders.')
            updates['supplier_id'] = payload['supplier_id']

        if payload.get('expected_date') is not None:
            updates['expected_date'] = self._parse_expected_date(payload['expected_date'])

        if payload.get('notes') is not None:
            updates['notes'] = payload['notes']

        if payload.get('items') is not None:
            if purchase_order.status != 'draft':
                raise ValueError('Purchase order items can only be updated while the purchase order is in draft.')
            updates['items'] = self._normalize_items(payload['items'])

        status = payload.get('status')
        if status is not None:
            status = status.strip().lower()
            if status != purchase_order.status:
                if purchase_order.status == 'draft' and status == 'pending':
                    updates['status'] = 'pending'
                else:
                    raise ValueError('Invalid purchase order status transition.')

        if not updates:
            raise ValueError('No valid fields provided for update.')

        purchase_order = self.repository.update(purchase_order, updates)
        event_name = 'PO_SUBMITTED' if updates.get('status') == 'pending' else 'PO_UPDATED'
        log_audit_event(user, request_context, event_name, f'purchase_order:{purchase_order.id}', 'success')
        return purchase_order

    def delete_purchase_order(self, user, purchase_order_id, request_context=None):
        purchase_order = self.repository.get_by_id(purchase_order_id)
        if purchase_order is None:
            raise ValueError('Purchase order not found')

        self.repository.delete(purchase_order)
        log_audit_event(user, request_context, 'PO_DELETED', f'purchase_order:{purchase_order.id}', 'success')

    def approve_purchase_order(self, user, purchase_order_id, request_context=None):
        purchase_order = self.repository.get_by_id(purchase_order_id)
        if purchase_order is None:
            raise ValueError('Purchase order not found')

        if purchase_order.status != 'pending':
            raise ValueError('Only pending purchase orders can be approved.')

        purchase_order.status = 'ordered'
        purchase_order.approved_by = user.get('user_id') or user.get('id')
        purchase_order.approved_at = utc_now()
        purchase_order.ordered_at = utc_now()

        db.session.add(purchase_order)
        db.session.commit()

        log_audit_event(user, request_context, 'PO_APPROVED', f'purchase_order:{purchase_order.id}', 'success')
        return purchase_order

    def receive_purchase_order(self, user, purchase_order_id, payload, request_context=None):
        purchase_order = self.repository.get_by_id(purchase_order_id)
        if purchase_order is None:
            raise ValueError('Purchase order not found')

        if purchase_order.status not in ('ordered', 'partially_received'):
            raise ValueError('Only ordered or partially_received purchase orders can be received.')

        receive_quantities = self._normalize_receive_items(payload.get('items'))
        if not receive_quantities:
            raise ValueError('At least one item must be provided for receiving.')

        items_by_id = {item.id: item for item in purchase_order.items}
        total_received = 0

        for item_id, quantity in receive_quantities.items():
            item = items_by_id.get(item_id)
            if item is None:
                raise ValueError(f'Purchase order item not found: {item_id}')

            remaining = item.quantity_ordered - item.quantity_received
            if quantity <= 0:
                raise ValueError('Quantity received must be greater than 0.')
            if quantity > remaining:
                raise ValueError('Quantity received cannot exceed remaining ordered quantity.')

            item.quantity_received += quantity
            total_received += quantity
            add_stock(
                product_id=item.product_id,
                supplier_id=purchase_order.supplier_id,
                quantity=quantity,
                note=f'Received from purchase order {purchase_order.po_number}',
                user_id=user.get('user_id') or user.get('id'),
                reference_type='PurchaseOrder',
                reference_id=purchase_order.id,
                commit=False,
            )

        if total_received == 0:
            raise ValueError('No quantities were received.')

        purchase_order.status = 'received' if all(item.quantity_received >= item.quantity_ordered for item in purchase_order.items) else 'partially_received'

        db.session.add(purchase_order)
        db.session.commit()

        log_audit_event(user, request_context, 'PO_RECEIVED', f'purchase_order:{purchase_order.id}', 'success')
        return purchase_order

    def cancel_purchase_order(self, user, purchase_order_id, payload, request_context=None):
        purchase_order = self.repository.get_by_id(purchase_order_id)
        if purchase_order is None:
            raise ValueError('Purchase order not found')

        if purchase_order.status not in ('draft', 'pending'):
            raise ValueError('Only draft or pending purchase orders can be cancelled.')

        if not isinstance(payload, dict):
            raise ValueError('Request payload must be a JSON object.')

        cancellation_reason = payload.get('cancellation_reason') or payload.get('reason')
        if not cancellation_reason:
            raise ValueError('Cancellation reason is required.')

        purchase_order.status = 'cancelled'
        purchase_order.cancellation_reason = cancellation_reason

        db.session.add(purchase_order)
        db.session.commit()

        log_audit_event(user, request_context, 'PO_CANCELLED', f'purchase_order:{purchase_order.id}', 'success')
        return purchase_order

    def _parse_expected_date(self, value):
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                raise ValueError('Expected date must be a valid ISO 8601 date string.')
        raise ValueError('Expected date must be a string in ISO 8601 format.')

    def _normalize_items(self, items):
        if not isinstance(items, list) or not items:
            raise ValueError('Purchase order items are required.')

        normalized_items = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Each purchase order item must be an object.')

            product_id = item.get('product_id')
            quantity_ordered = item.get('quantity_ordered')
            unit_cost = item.get('unit_cost')

            if product_id is None or quantity_ordered is None or unit_cost is None:
                raise ValueError('Each item must include product_id, quantity_ordered, and unit_cost.')

            try:
                product_id = int(product_id)
                quantity_ordered = int(quantity_ordered)
                unit_cost = Decimal(str(unit_cost))
            except (TypeError, ValueError):
                raise ValueError('Invalid item payload for purchase order items.')

            if product_id <= 0 or quantity_ordered <= 0:
                raise ValueError('product_id and quantity_ordered must be positive integers.')

            if unit_cost < 0:
                raise ValueError('unit_cost cannot be negative.')

            product = db.session.get(Product, product_id)
            if product is None:
                raise ValueError(f'Product not found: {product_id}')

            normalized_items.append({
                'product_id': product_id,
                'quantity_ordered': quantity_ordered,
                'unit_cost': unit_cost,
            })

        return normalized_items

    def _normalize_receive_items(self, items):
        if not isinstance(items, list) or not items:
            raise ValueError('Receive payload must include a list of items.')

        quantities = {}
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Each received item must be an object.')

            item_id = item.get('item_id')
            quantity_received = item.get('quantity_received')
            if item_id is None or quantity_received is None:
                raise ValueError('Each received item must include item_id and quantity_received.')

            try:
                item_id = int(item_id)
                quantity_received = int(quantity_received)
            except (TypeError, ValueError):
                raise ValueError('Invalid receive payload for purchase order items.')

            if item_id <= 0 or quantity_received <= 0:
                raise ValueError('item_id and quantity_received must be positive integers.')

            quantities[item_id] = quantity_received

        return quantities


PurchaseOrderService = PurchaseOrderAPIService
