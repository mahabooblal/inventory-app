from flask import Blueprint, g, request

from app.api.authz import role_required, token_required
from app.api.response import json_error, json_paginated, json_success
from app.api.utils import ValidationError, get_filter_and_sort_params, get_pagination_params, parse_search_params, require_json
from app.services.purchase_order_api_service import PurchaseOrderService

bp = Blueprint('api_purchase_orders', __name__, url_prefix='/api/v1/purchase-orders')
service = PurchaseOrderService()


def serialize_item(item):
    return {
        'id': item.id,
        'product_id': item.product_id,
        'product_name': item.product.name if item.product else None,
        'quantity_ordered': item.quantity_ordered,
        'quantity_received': item.quantity_received,
        'remaining_quantity': item.quantity_ordered - item.quantity_received,
        'unit_cost': float(item.unit_cost or 0),
    }


def serialize_purchase_order(order):
    return {
        'id': order.id,
        'po_number': order.po_number,
        'supplier_id': order.supplier_id,
        'supplier_name': order.supplier.name if order.supplier else None,
        'status': order.status,
        'expected_date': order.expected_date.isoformat() if order.expected_date else None,
        'notes': order.notes,
        'total_amount': float(order.total_amount or 0),
        'created_by': order.created_by,
        'approved_by': order.approved_by,
        'approved_at': order.approved_at.isoformat() if order.approved_at else None,
        'ordered_at': order.ordered_at.isoformat() if order.ordered_at else None,
        'created_at': order.created_at.isoformat() if order.created_at else None,
        'updated_at': order.updated_at.isoformat() if order.updated_at else None,
        'items': [serialize_item(item) for item in order.items],
    }


@bp.route('', methods=['GET'])
@token_required(token_type='access')
def list_purchase_orders():
    filters, sort_by, sort_order = get_filter_and_sort_params()
    page, per_page = get_pagination_params()
    search = parse_search_params()

    purchase_orders, total = service.list_purchase_orders(
        filters=filters,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
    )

    return json_paginated(
        [serialize_purchase_order(po) for po in purchase_orders],
        total,
        page,
        per_page,
    )


@bp.route('/<int:purchase_order_id>', methods=['GET'])
@token_required(token_type='access')
def get_purchase_order(purchase_order_id):
    purchase_order = service.get_purchase_order(purchase_order_id)
    if purchase_order is None:
        return json_error('Purchase order not found', error_code='PURCHASE_ORDER_NOT_FOUND', status_code=404)
    return json_success(serialize_purchase_order(purchase_order))


@bp.route('', methods=['POST'])
@token_required(token_type='access')
@role_required('manager', 'admin')
def create_purchase_order():
    payload = require_json()
    try:
        purchase_order = service.create_purchase_order(g.jwt_payload, payload, request)
    except ValidationError as exc:
        return json_error(str(exc), error_code='VALIDATION_ERROR', status_code=400)
    except ValueError as exc:
        return json_error(str(exc), error_code='PURCHASE_ORDER_CREATION_FAILED', status_code=400)

    return json_success(serialize_purchase_order(purchase_order), status_code=201)


@bp.route('/<int:purchase_order_id>', methods=['PUT'])
@token_required(token_type='access')
@role_required('manager', 'admin')
def update_purchase_order(purchase_order_id):
    payload = require_json()
    try:
        purchase_order = service.update_purchase_order(g.jwt_payload, purchase_order_id, payload, request)
    except ValidationError as exc:
        return json_error(str(exc), error_code='VALIDATION_ERROR', status_code=400)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            return json_error(message, error_code='PURCHASE_ORDER_NOT_FOUND', status_code=404)
        return json_error(message, error_code='PURCHASE_ORDER_UPDATE_FAILED', status_code=400)

    return json_success(serialize_purchase_order(purchase_order))


@bp.route('/<int:purchase_order_id>', methods=['DELETE'])
@token_required(token_type='access')
@role_required('admin')
def delete_purchase_order(purchase_order_id):
    try:
        service.delete_purchase_order(g.jwt_payload, purchase_order_id, request)
    except ValueError as exc:
        return json_error(str(exc), error_code='PURCHASE_ORDER_NOT_FOUND', status_code=404)

    return json_success({'deleted': purchase_order_id})


@bp.route('/<int:purchase_order_id>/approve', methods=['POST'])
@token_required(token_type='access')
@role_required('admin')
def approve_purchase_order(purchase_order_id):
    try:
        purchase_order = service.approve_purchase_order(g.jwt_payload, purchase_order_id, request)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            return json_error(message, error_code='PURCHASE_ORDER_NOT_FOUND', status_code=404)
        return json_error(message, error_code='PURCHASE_ORDER_APPROVAL_FAILED', status_code=400)

    return json_success(serialize_purchase_order(purchase_order))


@bp.route('/<int:purchase_order_id>/receive', methods=['POST'])
@token_required(token_type='access')
@role_required('manager', 'admin')
def receive_purchase_order(purchase_order_id):
    payload = require_json()
    try:
        purchase_order = service.receive_purchase_order(g.jwt_payload, purchase_order_id, payload, request)
    except ValidationError as exc:
        return json_error(str(exc), error_code='VALIDATION_ERROR', status_code=400)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            return json_error(message, error_code='PURCHASE_ORDER_NOT_FOUND', status_code=404)
        return json_error(message, error_code='PURCHASE_ORDER_RECEIVE_FAILED', status_code=400)

    return json_success(serialize_purchase_order(purchase_order))


@bp.route('/<int:purchase_order_id>/cancel', methods=['POST'])
@token_required(token_type='access')
@role_required('manager', 'admin')
def cancel_purchase_order(purchase_order_id):
    try:
        purchase_order = service.cancel_purchase_order(g.jwt_payload, purchase_order_id, require_json(), request)
    except ValidationError as exc:
        return json_error(str(exc), error_code='VALIDATION_ERROR', status_code=400)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            return json_error(message, error_code='PURCHASE_ORDER_NOT_FOUND', status_code=404)
        return json_error(message, error_code='PURCHASE_ORDER_CANCELLATION_FAILED', status_code=400)

    return json_success(serialize_purchase_order(purchase_order))
