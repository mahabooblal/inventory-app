from flask import Blueprint, g, request

from app.api.authz import role_required, token_required
from app.api.response import json_error, json_paginated, json_success
from app.api.utils import ValidationError, get_filter_and_sort_params, get_pagination_params, parse_search_params, require_json
from app.services.sale_api_service import SaleService

bp = Blueprint('api_sales', __name__, url_prefix='/api/v1/sales')
service = SaleService()


def serialize_sale(sale):
    return {
        'id': sale.id,
        'product_id': sale.product_id,
        'product_name': sale.product.name if sale.product else None,
        'customer_id': sale.customer_id,
        'customer_name': sale.customer.name if sale.customer else None,
        'quantity': sale.quantity,
        'selling_price': float(sale.selling_price or 0),
        'total_amount': float(sale.total_amount or 0),
        'destination_details': sale.destination_details,
        'sale_date': sale.sale_date.isoformat() if sale.sale_date else None,
        'created_by': sale.created_by,
    }


@bp.route('', methods=['GET'])
@token_required(token_type='access')
def list_sales():
    filters, sort_by, sort_order = get_filter_and_sort_params()
    page, per_page = get_pagination_params()
    search = parse_search_params()

    sales, total = service.list_sales(
        filters=filters,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
    )

    return json_paginated([serialize_sale(sale) for sale in sales], total, page, per_page)


@bp.route('/<int:sale_id>', methods=['GET'])
@token_required(token_type='access')
def get_sale(sale_id):
    sale = service.get_sale(sale_id)
    if sale is None:
        return json_error('Sale not found', error_code='SALE_NOT_FOUND', status_code=404)
    return json_success(serialize_sale(sale))


@bp.route('', methods=['POST'])
@token_required(token_type='access')
def create_sale():
    payload = require_json()
    try:
        sale = service.create_sale(g.jwt_payload, payload, request)
    except ValidationError as exc:
        return json_error(str(exc), error_code='VALIDATION_ERROR', status_code=400)
    except ValueError as exc:
        return json_error(str(exc), error_code='SALE_CREATION_FAILED', status_code=400)

    return json_success(serialize_sale(sale), status_code=201)
