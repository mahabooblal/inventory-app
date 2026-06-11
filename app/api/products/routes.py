"""Products API routes."""

from flask import Blueprint, request, g
from app.api.response import json_error, json_paginated, json_success
from app.api.authz import role_required, token_required
from app.api.utils import ValidationError, get_filter_and_sort_params, get_pagination_params, parse_search_params, require_json
from app.services.product_service import ProductService

bp = Blueprint('api_products', __name__, url_prefix='/api/v1/products')
product_service = ProductService()


def serialize_product(product):
    return {
        'id': product.id,
        'name': product.name,
        'sku': product.sku,
        'barcode': product.barcode,
        'description': product.description,
        'image_filename': product.image_filename,
        'is_active': product.is_active,
        'price': float(product.price) if product.price is not None else None,
        'cost_price': float(product.cost_price) if product.cost_price is not None else None,
        'quantity': product.quantity,
        'low_stock_limit': product.low_stock_limit,
        'category': {
            'id': product.category.id,
            'name': product.category.name,
        } if getattr(product, 'category', None) else None,
        'supplier': {
            'id': product.supplier.id,
            'name': product.supplier.name,
        } if getattr(product, 'supplier', None) else None,
        'created_at': product.created_at.isoformat() if product.created_at else None,
        'updated_at': product.updated_at.isoformat() if product.updated_at else None,
    }


@bp.route('', methods=['GET'])
@token_required(token_type='access')
def list_products():
    filters, sort_by, sort_order = get_filter_and_sort_params()
    page, per_page = get_pagination_params()
    search = parse_search_params()

    products, total = product_service.list_products(
        filters=filters,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
    )

    serialized = [serialize_product(product) for product in products]
    return json_paginated(serialized, total=total, page=page, per_page=per_page)


@bp.route('/<int:product_id>', methods=['GET'])
@token_required(token_type='access')
def get_product(product_id):
    try:
        product = product_service.get_product(product_id)
    except ValueError as exc:
        return json_error(str(exc), error_code='PRODUCT_NOT_FOUND', status_code=404)

    return json_success(serialize_product(product))


@bp.route('', methods=['POST'])
@token_required(token_type='access')
@role_required('manager', 'admin')
def create_product():
    user = getattr(g, 'jwt_payload', None)
    if not user:
        return json_error('Authenticated user not found', error_code='USER_NOT_FOUND', status_code=404)

    try:
        payload = require_json()
        product = product_service.create_product(user, payload, request)
        return json_success(serialize_product(product), status_code=201)
    except ValidationError as exc:
        return json_error(exc.message, error_code=exc.error_code, errors=exc.errors, status_code=exc.status_code)
    except ValueError as exc:
        return json_error(str(exc), error_code='PRODUCT_CREATION_FAILED', status_code=400)


@bp.route('/<int:product_id>', methods=['PUT'])
@token_required(token_type='access')
@role_required('manager', 'admin')
def update_product(product_id):
    user = getattr(g, 'jwt_payload', None)
    if not user:
        return json_error('Authenticated user not found', error_code='USER_NOT_FOUND', status_code=404)

    try:
        payload = require_json()
        product = product_service.update_product(user, product_id, payload, request)
        return json_success(serialize_product(product))
    except ValidationError as exc:
        return json_error(exc.message, error_code=exc.error_code, errors=exc.errors, status_code=exc.status_code)
    except ValueError as exc:
        return json_error(str(exc), error_code='PRODUCT_UPDATE_FAILED', status_code=404 if 'not found' in str(exc).lower() else 400)


@bp.route('/<int:product_id>', methods=['DELETE'])
@token_required(token_type='access')
@role_required('admin')
def delete_product(product_id):
    user = getattr(g, 'jwt_payload', None)
    if not user:
        return json_error('Authenticated user not found', error_code='USER_NOT_FOUND', status_code=404)

    try:
        product_service.delete_product(user, product_id, request)
        return json_success({'id': product_id, 'deleted': True})
    except ValueError as exc:
        return json_error(str(exc), error_code='PRODUCT_DELETE_FAILED', status_code=404)
