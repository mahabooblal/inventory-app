from flask import Blueprint, g, request

from app.api.authz import role_required, token_required
from app.api.response import json_error, json_paginated, json_success
from app.api.utils import get_filter_and_sort_params, get_pagination_params, parse_search_params, require_json
from app.services.warehouse_api_service import WarehouseService

bp = Blueprint('warehouses_api', __name__, url_prefix='/api/v1/warehouses')
service = WarehouseService()


def serialize_warehouse(warehouse):
    return {
        'id': warehouse.id,
        'name': warehouse.name,
        'code': warehouse.code,
        'address': warehouse.address,
        'is_active': warehouse.is_active,
        'created_at': warehouse.created_at.isoformat() if warehouse.created_at else None,
        'updated_at': getattr(warehouse, 'updated_at', None).isoformat() if getattr(warehouse, 'updated_at', None) else None,
    }


def serialize_inventory_entry(entry):
    warehouse_stock, product = entry
    return {
        'product_id': product.id,
        'product_name': product.name,
        'sku': product.sku,
        'quantity': warehouse_stock.quantity,
        'warehouse_id': warehouse_stock.warehouse_id,
        'updated_at': warehouse_stock.updated_at.isoformat() if warehouse_stock.updated_at else None,
    }


def serialize_movement_entry(entry, warehouse_id):
    transfer, product = entry
    direction = 'outgoing' if transfer.source_warehouse_id == warehouse_id else 'incoming'
    return {
        'id': transfer.id,
        'product_id': product.id,
        'product_name': product.name,
        'sku': product.sku,
        'quantity': transfer.quantity,
        'direction': direction,
        'source_warehouse_id': transfer.source_warehouse_id,
        'destination_warehouse_id': transfer.destination_warehouse_id,
        'status': transfer.status,
        'created_at': transfer.created_at.isoformat() if transfer.created_at else None,
        'note': transfer.note,
    }


@bp.route('/', methods=['GET'], strict_slashes=False)
@token_required(token_type='access')
def list_warehouses():
    page, per_page = get_pagination_params()
    filters, sort_by, sort_order = get_filter_and_sort_params()
    search = parse_search_params()
    warehouses, total = service.list_warehouses(filters, search, sort_by, sort_order, page, per_page)
    return json_paginated([serialize_warehouse(w) for w in warehouses], total, page, per_page)


@bp.route('/<int:warehouse_id>', methods=['GET'])
@token_required(token_type='access')
def get_warehouse(warehouse_id):
    try:
        warehouse = service.get_warehouse(warehouse_id)
    except ValueError as exc:
        return json_error(str(exc), error_code='NOT_FOUND', status_code=404)
    return json_success(serialize_warehouse(warehouse))


@bp.route('/', methods=['POST'], strict_slashes=False)
@token_required(token_type='access')
@role_required('manager', 'admin')
def create_warehouse():
    payload = require_json()
    try:
        warehouse = service.create_warehouse(g.jwt_payload, payload, request)
    except ValueError as exc:
        return json_error(str(exc), error_code='VALIDATION_FAILED', status_code=400)
    return json_success(serialize_warehouse(warehouse), status_code=201)


@bp.route('/<int:warehouse_id>', methods=['PUT'])
@token_required(token_type='access')
@role_required('manager', 'admin')
def update_warehouse(warehouse_id):
    payload = require_json()
    try:
        warehouse = service.update_warehouse(g.jwt_payload, warehouse_id, payload, request)
    except ValueError as exc:
        status_code = 404 if 'not found' in str(exc).lower() else 400
        error_code = 'NOT_FOUND' if status_code == 404 else 'VALIDATION_FAILED'
        return json_error(str(exc), error_code=error_code, status_code=status_code)
    return json_success(serialize_warehouse(warehouse))


@bp.route('/<int:warehouse_id>', methods=['DELETE'])
@token_required(token_type='access')
@role_required('admin')
def delete_warehouse(warehouse_id):
    try:
        service.delete_warehouse(g.jwt_payload, warehouse_id, request)
    except ValueError as exc:
        return json_error(str(exc), error_code='NOT_FOUND', status_code=404)
    return json_success({'deleted': warehouse_id})


@bp.route('/<int:warehouse_id>/inventory', methods=['GET'])
@token_required(token_type='access')
def get_warehouse_inventory(warehouse_id):
    page, per_page = get_pagination_params()
    filters, sort_by, sort_order = get_filter_and_sort_params()
    search = parse_search_params()
    try:
        records, total = service.list_inventory(warehouse_id, filters, search, sort_by, sort_order, page, per_page)
    except ValueError as exc:
        return json_error(str(exc), error_code='NOT_FOUND', status_code=404)
    return json_paginated([serialize_inventory_entry(entry) for entry in records], total, page, per_page)


@bp.route('/<int:warehouse_id>/movements', methods=['GET'])
@token_required(token_type='access')
def get_warehouse_movements(warehouse_id):
    page, per_page = get_pagination_params()
    filters, sort_by, sort_order = get_filter_and_sort_params()
    search = parse_search_params()
    try:
        records, total = service.list_movements(warehouse_id, filters, search, sort_by, sort_order, page, per_page)
    except ValueError as exc:
        return json_error(str(exc), error_code='NOT_FOUND', status_code=404)
    return json_paginated([serialize_movement_entry(entry, warehouse_id) for entry in records], total, page, per_page)
