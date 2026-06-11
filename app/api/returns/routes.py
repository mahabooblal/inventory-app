from flask import Blueprint, g, request

from app.api.authz import role_required, token_required
from app.api.response import json_error, json_paginated, json_success
from app.api.utils import ValidationError, get_filter_and_sort_params, get_pagination_params, parse_search_params, require_json
from app.services.return_api_service import ReturnService

bp = Blueprint('api_returns', __name__, url_prefix='/api/v1/returns')
service = ReturnService()


def serialize_return(order):
    return {
        'id': order.id,
        'return_number': order.return_number,
        'return_type': order.return_type,
        'product_id': order.product_id,
        'product_name': order.product.name if order.product else None,
        'customer_id': order.customer_id,
        'customer_name': order.customer.name if order.customer else None,
        'supplier_id': order.supplier_id,
        'supplier_name': order.supplier.name if order.supplier else None,
        'quantity': order.quantity,
        'refund_amount': float(order.refund_amount or 0),
        'restock': order.restock,
        'reason': order.reason,
        'status': order.status,
        'rejection_reason': order.rejection_reason,
        'cancellation_reason': order.cancellation_reason,
        'approved_by': order.approved_by,
        'approved_at': order.approved_at.isoformat() if order.approved_at else None,
        'created_by': order.created_by,
        'created_at': order.created_at.isoformat() if order.created_at else None,
    }


@bp.route('', methods=['GET'])
@token_required(token_type='access')
def list_returns():
    filters, sort_by, sort_order = get_filter_and_sort_params()
    page, per_page = get_pagination_params()
    search = parse_search_params()

    returns, total = service.list_returns(
        filters=filters,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
    )

    return json_paginated([serialize_return(order) for order in returns], total, page, per_page)


@bp.route('/<int:return_order_id>', methods=['GET'])
@token_required(token_type='access')
def get_return(return_order_id):
    return_order = service.get_return(return_order_id)
    if return_order is None:
        return json_error('Return order not found', error_code='RETURN_ORDER_NOT_FOUND', status_code=404)
    return json_success(serialize_return(return_order))


@bp.route('', methods=['POST'])
@token_required(token_type='access')
def request_return():
    payload = require_json()
    try:
        return_order = service.request_return(g.jwt_payload, payload, request)
    except ValidationError as exc:
        return json_error(str(exc), error_code='VALIDATION_ERROR', status_code=400)
    except ValueError as exc:
        return json_error(str(exc), error_code='RETURN_REQUEST_FAILED', status_code=400)

    return json_success(serialize_return(return_order), status_code=201)


@bp.route('/<int:return_order_id>/approve', methods=['POST'])
@token_required(token_type='access')
@role_required('manager', 'admin')
def approve_return(return_order_id):
    try:
        return_order = service.approve_return(g.jwt_payload, return_order_id, request)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            return json_error(message, error_code='RETURN_ORDER_NOT_FOUND', status_code=404)
        return json_error(message, error_code='RETURN_APPROVAL_FAILED', status_code=400)

    return json_success(serialize_return(return_order))


@bp.route('/<int:return_order_id>/reject', methods=['POST'])
@token_required(token_type='access')
@role_required('manager', 'admin')
def reject_return(return_order_id):
    payload = require_json()
    try:
        return_order = service.reject_return(g.jwt_payload, return_order_id, payload, request)
    except ValidationError as exc:
        return json_error(str(exc), error_code='VALIDATION_ERROR', status_code=400)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            return json_error(message, error_code='RETURN_ORDER_NOT_FOUND', status_code=404)
        return json_error(message, error_code='RETURN_REJECTION_FAILED', status_code=400)

    return json_success(serialize_return(return_order))


@bp.route('/<int:return_order_id>/cancel', methods=['POST'])
@token_required(token_type='access')
def cancel_return(return_order_id):
    payload = require_json()
    try:
        return_order = service.cancel_return(g.jwt_payload, return_order_id, payload, request)
    except ValidationError as exc:
        return json_error(str(exc), error_code='VALIDATION_ERROR', status_code=400)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            return json_error(message, error_code='RETURN_ORDER_NOT_FOUND', status_code=404)
        return json_error(message, error_code='RETURN_CANCELLATION_FAILED', status_code=400)

    return json_success(serialize_return(return_order))
