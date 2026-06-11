from flask import Blueprint, g, request

from app.api.authz import role_required, token_required
from app.api.response import json_error, json_paginated, json_success
from app.api.utils import get_filter_and_sort_params, get_pagination_params, parse_search_params, require_json
from app.services.supplier_service import SupplierService

bp = Blueprint('suppliers_api', __name__, url_prefix='/api/v1/suppliers')
service = SupplierService()


def serialize_supplier(supplier):
    return {
        'id': supplier.id,
        'name': supplier.name,
        'email': supplier.email,
        'phone': supplier.phone,
        'address': supplier.address,
        'is_active': supplier.is_active,
        'created_at': supplier.created_at.isoformat() if supplier.created_at else None,
        'updated_at': getattr(supplier, 'updated_at', None).isoformat() if getattr(supplier, 'updated_at', None) else None,
    }


def serialize_product(product):
    return {
        'id': product.id,
        'name': product.name,
        'sku': product.sku,
        'barcode': product.barcode,
        'quantity': product.quantity,
        'is_active': product.is_active,
        'supplier_id': product.supplier_id,
    }


def serialize_purchase_order(order):
    return {
        'id': order.id,
        'po_number': order.po_number,
        'supplier_id': order.supplier_id,
        'status': order.status,
        'total_amount': order.total_amount,
        'created_at': order.created_at.isoformat() if order.created_at else None,
        'updated_at': getattr(order, 'updated_at', None).isoformat() if getattr(order, 'updated_at', None) else None,
    }


@bp.route('/', methods=['GET'], strict_slashes=False)
@token_required(token_type='access')
def list_suppliers():
    page, per_page = get_pagination_params()
    filters, sort_by, sort_order = get_filter_and_sort_params()
    search = parse_search_params()
    suppliers, total = service.list_suppliers(filters, search, sort_by, sort_order, page, per_page)
    return json_paginated([serialize_supplier(s) for s in suppliers], total, page, per_page)


@bp.route('/<int:supplier_id>', methods=['GET'])
@token_required(token_type='access')
def get_supplier(supplier_id):
    try:
        supplier = service.get_supplier(supplier_id)
    except ValueError as exc:
        return json_error(str(exc), error_code='NOT_FOUND', status_code=404)
    return json_success(serialize_supplier(supplier))


@bp.route('/', methods=['POST'], strict_slashes=False)
@token_required(token_type='access')
@role_required('manager', 'admin')
def create_supplier():
    payload = require_json()
    try:
        supplier = service.create_supplier(g.jwt_payload, payload, request)
    except ValueError as exc:
        return json_error(str(exc), error_code='VALIDATION_FAILED', status_code=400)
    return json_success(serialize_supplier(supplier), status_code=201)


@bp.route('/<int:supplier_id>', methods=['PUT'])
@token_required(token_type='access')
@role_required('manager', 'admin')
def update_supplier(supplier_id):
    payload = require_json()
    try:
        supplier = service.update_supplier(g.jwt_payload, supplier_id, payload, request)
    except ValueError as exc:
        status_code = 404 if 'not found' in str(exc).lower() else 400
        error_code = 'NOT_FOUND' if status_code == 404 else 'VALIDATION_FAILED'
        return json_error(str(exc), error_code=error_code, status_code=status_code)
    return json_success(serialize_supplier(supplier))


@bp.route('/<int:supplier_id>', methods=['DELETE'])
@token_required(token_type='access')
@role_required('admin')
def delete_supplier(supplier_id):
    try:
        service.delete_supplier(g.jwt_payload, supplier_id, request)
    except ValueError as exc:
        return json_error(str(exc), error_code='NOT_FOUND', status_code=404)
    return json_success({'deleted': supplier_id})


@bp.route('/<int:supplier_id>/products', methods=['GET'])
@token_required(token_type='access')
def get_supplier_products(supplier_id):
    page, per_page = get_pagination_params()
    filters, sort_by, sort_order = get_filter_and_sort_params()
    search = parse_search_params()
    try:
        products, total = service.list_products(supplier_id, filters, search, sort_by, sort_order, page, per_page)
    except ValueError as exc:
        return json_error(str(exc), error_code='NOT_FOUND', status_code=404)
    return json_paginated([serialize_product(p) for p in products], total, page, per_page)


@bp.route('/<int:supplier_id>/purchase-orders', methods=['GET'])
@token_required(token_type='access')
def get_supplier_purchase_orders(supplier_id):
    page, per_page = get_pagination_params()
    filters, sort_by, sort_order = get_filter_and_sort_params()
    search = parse_search_params()
    try:
        orders, total = service.list_purchase_orders(supplier_id, filters, search, sort_by, sort_order, page, per_page)
    except ValueError as exc:
        return json_error(str(exc), error_code='NOT_FOUND', status_code=404)
    return json_paginated([serialize_purchase_order(o) for o in orders], total, page, per_page)
