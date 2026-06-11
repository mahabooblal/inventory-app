import pytest
from decimal import Decimal

from app import db
from app.models import Supplier, PurchaseOrder
from app.repositories.purchase_order_repository import PurchaseOrderRepository
from app.services.purchase_order_api_service import PurchaseOrderAPIService


def create_purchase_order_payload(supplier_id, product_id, quantity=2, unit_cost=4.5, expected_date=None):
    payload = {
        'supplier_id': supplier_id,
        'items': [
            {
                'product_id': product_id,
                'quantity_ordered': quantity,
                'unit_cost': unit_cost,
            }
        ],
    }
    if expected_date is not None:
        payload['expected_date'] = expected_date
    return payload


def test_purchase_order_service_create_and_input_validation(manager_user, supplier, product, database):
    service = PurchaseOrderAPIService()
    user = {'user_id': manager_user.id, 'username': manager_user.username}

    payload = create_purchase_order_payload(supplier.id, product.id, quantity=2, unit_cost=5.5, expected_date='2026-12-31')
    order = service.create_purchase_order(user, payload)

    assert order.status == 'draft'
    assert order.supplier_id == supplier.id
    assert order.total_amount == Decimal('11.00')
    assert order.expected_date.isoformat() == '2026-12-31'
    assert order.items[0].quantity_ordered == 2

    with pytest.raises(ValueError, match='Supplier id is required'):
        service.create_purchase_order(user, {'items': payload['items']})

    with pytest.raises(ValueError, match='Purchase order items are required'):
        service.create_purchase_order(user, {'supplier_id': supplier.id, 'items': []})

    with pytest.raises(ValueError, match='Product not found'):
        service.create_purchase_order(user, {'supplier_id': supplier.id, 'items': [{'product_id': 999999, 'quantity_ordered': 1, 'unit_cost': 1.0}]})

    with pytest.raises(ValueError, match='Expected date must be a valid ISO 8601 date string'):
        service.create_purchase_order(user, {'supplier_id': supplier.id, 'items': payload['items'], 'expected_date': 'invalid-date'})


def test_purchase_order_service_update_transitions_and_error_paths(admin_user, supplier, product, database):
    service = PurchaseOrderAPIService()
    user = {'user_id': admin_user.id, 'username': admin_user.username}

    payload = create_purchase_order_payload(supplier.id, product.id)
    order = service.create_purchase_order(user, payload)

    order = service.update_purchase_order(user, order.id, {'status': 'pending', 'notes': 'Submit order'})
    assert order.status == 'pending'
    assert order.notes == 'Submit order'

    with pytest.raises(ValueError, match='Purchase order items can only be updated while the purchase order is in draft'):
        service.update_purchase_order(user, order.id, {'items': payload['items']})

    with pytest.raises(ValueError, match='Supplier id can only be updated for draft purchase orders'):
        service.update_purchase_order(user, order.id, {'supplier_id': 999999})

    with pytest.raises(ValueError, match='Invalid purchase order status transition'):
        service.update_purchase_order(user, order.id, {'status': 'draft'})

    with pytest.raises(ValueError, match='Request payload must be a JSON object'):
        service.update_purchase_order(user, order.id, {})

    with pytest.raises(ValueError, match='Purchase order not found'):
        service.update_purchase_order(user, 999999, {'notes': 'Missing order'})


def test_purchase_order_service_approve_receive_and_cancel_workflow(admin_user, manager_user, supplier, product, database):
    service = PurchaseOrderAPIService()
    creator = {'user_id': manager_user.id, 'username': manager_user.username}
    approver = {'user_id': admin_user.id, 'username': admin_user.username}

    payload = create_purchase_order_payload(supplier.id, product.id, quantity=2, unit_cost=3.0)
    order = service.create_purchase_order(creator, payload)
    order = service.update_purchase_order(creator, order.id, {'status': 'pending'})

    order = service.approve_purchase_order(approver, order.id)
    assert order.status == 'ordered'

    with pytest.raises(ValueError, match='Only pending purchase orders can be approved'):
        service.approve_purchase_order(approver, order.id)

    with pytest.raises(ValueError, match='Purchase order not found'):
        service.receive_purchase_order(approver, 999999, {'items': [{'item_id': 1, 'quantity_received': 1}]})

    with pytest.raises(ValueError, match='Receive payload must include a list of items'):
        service.receive_purchase_order(approver, order.id, {'items': []})

    item_id = order.items[0].id
    with pytest.raises(ValueError, match='item_id and quantity_received must be positive integers'):
        service.receive_purchase_order(approver, order.id, {'items': [{'item_id': item_id, 'quantity_received': 0}]})

    with pytest.raises(ValueError, match='Quantity received cannot exceed remaining ordered quantity'):
        service.receive_purchase_order(approver, order.id, {'items': [{'item_id': item_id, 'quantity_received': 3}]})

    order = service.receive_purchase_order(approver, order.id, {'items': [{'item_id': item_id, 'quantity_received': 1}]})
    assert order.status == 'partially_received'

    order = service.receive_purchase_order(approver, order.id, {'items': [{'item_id': item_id, 'quantity_received': 1}]})
    assert order.status == 'received'

    with pytest.raises(ValueError, match='Only draft or pending purchase orders can be cancelled'):
        service.cancel_purchase_order(approver, order.id, {'cancellation_reason': 'No longer needed'})

    cancel_order = service.create_purchase_order(creator, payload)
    with pytest.raises(ValueError, match='Cancellation reason is required'):
        service.cancel_purchase_order(creator, cancel_order.id, {})

    cancelled = service.cancel_purchase_order(creator, cancel_order.id, {'reason': 'Ordered by mistake'})
    assert cancelled.status == 'cancelled'
    assert cancelled.cancellation_reason == 'Ordered by mistake'


def test_purchase_order_repository_list_search_sort_and_update_branches(product, supplier, database):
    repository = PurchaseOrderRepository()
    supplier_b = Supplier(name='Beta Supplies', email='beta@example.com', phone='555-9999', address='456 Other St')
    db.session.add(supplier_b)
    db.session.commit()

    order_one = repository.create(
        supplier_id=supplier.id,
        created_by=1,
        items=[{'product_id': product.id, 'quantity_ordered': 1, 'unit_cost': '1.00'}],
        notes='First order',
    )
    order_two = repository.create(
        supplier_id=supplier_b.id,
        created_by=1,
        items=[{'product_id': product.id, 'quantity_ordered': 2, 'unit_cost': '2.00'}],
        notes='Second order',
    )

    results, total = repository.list_purchase_orders(search=supplier.name)
    assert total == 1
    assert results[0].id == order_one.id

    results, total = repository.list_purchase_orders(filters={'status': 'draft'}, sort_by='po_number', sort_order='desc', page=1, per_page=1)
    assert total == 2
    assert len(results) == 1

    found = repository.get_by_id(order_one.id)
    assert found is not None
    assert found.supplier_id == supplier.id

    assert repository.get_by_id(999999) is None

    with pytest.raises(ValueError, match='Supplier not found'):
        repository.update(order_one, {'supplier_id': 999999})

    with pytest.raises(ValueError, match='Product not found'):
        repository.update(order_one, {'items': [{'product_id': 999999, 'quantity_ordered': 1, 'unit_cost': '1.00'}]})

    repository.delete(order_two)
    assert repository.get_by_id(order_two.id) is None


def test_purchase_order_service_additional_validation_paths(admin_user, supplier, product, database):
    service = PurchaseOrderAPIService()
    user = {'user_id': admin_user.id, 'username': admin_user.username}

    with pytest.raises(ValueError, match='Each purchase order item must be an object'):
        service.create_purchase_order(user, {'supplier_id': supplier.id, 'items': ['invalid']})

    with pytest.raises(ValueError, match='Each item must include product_id, quantity_ordered, and unit_cost'):
        service.create_purchase_order(user, {'supplier_id': supplier.id, 'items': [{'product_id': product.id, 'quantity_ordered': 1}]})

    with pytest.raises(ValueError, match='Invalid item payload'):
        service.create_purchase_order(user, {'supplier_id': supplier.id, 'items': [{'product_id': product.id, 'quantity_ordered': 'x', 'unit_cost': 1.0}]})

    with pytest.raises(ValueError, match='product_id and quantity_ordered must be positive integers'):
        service.create_purchase_order(user, {'supplier_id': supplier.id, 'items': [{'product_id': 0, 'quantity_ordered': 1, 'unit_cost': 1.0}]})

    with pytest.raises(ValueError, match='unit_cost cannot be negative'):
        service.create_purchase_order(user, {'supplier_id': supplier.id, 'items': [{'product_id': product.id, 'quantity_ordered': 1, 'unit_cost': -1.0}]})

    order = service.create_purchase_order(user, create_purchase_order_payload(supplier.id, product.id))

    with pytest.raises(ValueError, match='Request payload must be a JSON object'):
        service.update_purchase_order(user, order.id, None)

    with pytest.raises(ValueError, match='Only ordered or partially_received purchase orders can be received'):
        service.receive_purchase_order(user, order.id, {'items': [{'item_id': order.items[0].id, 'quantity_received': 1}]})

    with pytest.raises(ValueError, match='Request payload must be a JSON object'):
        service.cancel_purchase_order(user, order.id, None)

    with pytest.raises(ValueError, match='Cancellation reason is required'):
        service.cancel_purchase_order(user, order.id, {})

    with pytest.raises(ValueError, match='Purchase order not found'):
        service.approve_purchase_order(user, 999999)

    order = service.update_purchase_order(user, order.id, {'status': 'pending'})
    order = service.approve_purchase_order(user, order.id)

    with pytest.raises(ValueError, match='Each received item must include item_id and quantity_received'):
        service.receive_purchase_order(user, order.id, {'items': [{'item_id': None}]})

    with pytest.raises(ValueError, match='Invalid receive payload for purchase order items'):
        service.receive_purchase_order(user, order.id, {'items': [{'item_id': order.items[0].id, 'quantity_received': 'x'}]})

    from datetime import date
    order_with_date = service.create_purchase_order(user, {**create_purchase_order_payload(supplier.id, product.id), 'expected_date': date.today()})
    assert order_with_date.expected_date == date.today()
