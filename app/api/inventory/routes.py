"""Inventory API routes."""

from flask import Blueprint, request, g
from app.api.response import json_error, json_paginated, json_success
from app.api.authz import token_required
from app.api.utils import get_filter_and_sort_params, get_pagination_params, parse_search_params
from app.services.inventory_api_service import InventoryService

bp = Blueprint('api_inventory', __name__, url_prefix='/api/v1/inventory')
service = InventoryService()


def serialize_stock_level(entry):
    return {
        'product_id': entry['product_id'],
        'product_name': entry['product_name'],
        'sku': entry['sku'],
        'warehouse_id': entry['warehouse_id'],
        'warehouse_name': entry['warehouse_name'],
        'quantity': entry['quantity'],
        'unit_cost': entry['unit_cost'],
        'total_value': entry['total_value'],
    }


def serialize_stock_movement(entry):
    return {
        'id': entry['id'],
        'product_id': entry['product_id'],
        'product_name': entry['product_name'],
        'sku': entry['sku'],
        'movement_type': entry['movement_type'],
        'quantity': entry['quantity'],
        'quantity_before': entry['quantity_before'],
        'quantity_after': entry['quantity_after'],
        'unit_cost': entry['unit_cost'],
        'reference_type': entry['reference_type'],
        'reference_id': entry['reference_id'],
        'note': entry['note'],
        'created_at': entry['created_at'],
    }


def serialize_low_stock_item(entry):
    return {
        'product_id': entry['product_id'],
        'product_name': entry['product_name'],
        'sku': entry['sku'],
        'quantity': entry['quantity'],
        'low_stock_limit': entry['low_stock_limit'],
        'is_low_stock': entry['is_low_stock'],
        'warehouse_id': entry.get('warehouse_id'),
        'warehouse_name': entry.get('warehouse_name'),
    }


def serialize_valuation(entry):
    return {
        'product_id': entry['product_id'],
        'product_name': entry['product_name'],
        'sku': entry['sku'],
        'warehouse_id': entry.get('warehouse_id'),
        'warehouse_name': entry.get('warehouse_name'),
        'quantity': entry['quantity'],
        'unit_cost': entry['unit_cost'],
        'value': entry['value'],
    }


def _build_inventory_filters():
    filters, sort_by, sort_order = get_filter_and_sort_params()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date is not None:
        filters['start_date'] = start_date
    if end_date is not None:
        filters['end_date'] = end_date
    return filters, sort_by, sort_order


@bp.route('', methods=['GET'])
@token_required(token_type='access')
def list_stock_levels():
    user = getattr(g, 'jwt_payload', None)
    if not user:
        return json_error('Authenticated user not found', error_code='USER_NOT_FOUND', status_code=404)

    filters, sort_by, sort_order = _build_inventory_filters()
    page, per_page = get_pagination_params()
    search = parse_search_params()

    try:
        entries, total = service.list_stock_levels(
            user,
            request,
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )
    except ValueError as exc:
        return json_error(str(exc), status_code=400, error_code='INVALID_DATE_FILTER')

    return json_paginated([serialize_stock_level(entry) for entry in entries], total=total, page=page, per_page=per_page)


@bp.route('/movements', methods=['GET'])
@token_required(token_type='access')
def list_stock_movements():
    user = getattr(g, 'jwt_payload', None)
    if not user:
        return json_error('Authenticated user not found', error_code='USER_NOT_FOUND', status_code=404)

    filters, sort_by, sort_order = _build_inventory_filters()
    page, per_page = get_pagination_params()
    search = parse_search_params()

    try:
        entries, total = service.list_stock_movements(
            user,
            request,
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )
    except ValueError as exc:
        return json_error(str(exc), status_code=400, error_code='INVALID_DATE_FILTER')

    return json_paginated([serialize_stock_movement(entry) for entry in entries], total=total, page=page, per_page=per_page)


@bp.route('/low-stock', methods=['GET'])
@token_required(token_type='access')
def list_low_stock_items():
    user = getattr(g, 'jwt_payload', None)
    if not user:
        return json_error('Authenticated user not found', error_code='USER_NOT_FOUND', status_code=404)

    filters, sort_by, sort_order = get_filter_and_sort_params()
    page, per_page = get_pagination_params()
    search = parse_search_params()

    entries, total = service.list_low_stock_items(
        user,
        request,
        filters=filters,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
    )
    return json_paginated([serialize_low_stock_item(entry) for entry in entries], total=total, page=page, per_page=per_page)


@bp.route('/valuation', methods=['GET'])
@token_required(token_type='access')
def list_inventory_valuation():
    user = getattr(g, 'jwt_payload', None)
    if not user:
        return json_error('Authenticated user not found', error_code='USER_NOT_FOUND', status_code=404)

    filters, sort_by, sort_order = _build_inventory_filters()
    page, per_page = get_pagination_params()
    search = parse_search_params()

    try:
        entries, total = service.list_inventory_valuation(
            user,
            request,
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )
    except ValueError as exc:
        return json_error(str(exc), status_code=400, error_code='INVALID_DATE_FILTER')

    return json_paginated([serialize_valuation(entry) for entry in entries], total=total, page=page, per_page=per_page)
