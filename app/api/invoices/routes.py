from flask import Blueprint, g, request

from app.api.authz import role_required, token_required
from app.api.response import json_error, json_paginated, json_success
from app.api.utils import ValidationError, get_filter_and_sort_params, get_pagination_params, parse_search_params, require_json
from app.services.invoice_api_service import InvoiceService

bp = Blueprint('api_invoices', __name__, url_prefix='/api/v1/invoices')
service = InvoiceService()


def serialize_invoice_item(item):
    return {
        'id': item.id,
        'product_id': item.product_id,
        'quantity': item.quantity,
        'unit_price': float(item.unit_price or 0),
        'discount_amount': float(item.discount_amount or 0),
        'tax_rate': float(item.tax_rate or 0),
        'tax_amount': float(item.tax_amount or 0),
        'line_total': float(item.line_total or 0),
    }


def serialize_payment(payment):
    return {
        'id': payment.id,
        'invoice_id': payment.invoice_id,
        'amount': float(payment.amount or 0),
        'method': payment.method,
        'reference': payment.reference,
        'received_by': payment.received_by,
        'received_at': payment.received_at.isoformat() if payment.received_at else None,
    }


def serialize_invoice(invoice):
    return {
        'id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'customer_id': invoice.customer_id,
        'customer_name': invoice.customer.name if invoice.customer else None,
        'status': invoice.status,
        'subtotal': float(invoice.subtotal or 0),
        'discount_amount': float(invoice.discount_amount or 0),
        'tax_amount': float(invoice.tax_amount or 0),
        'total_amount': float(invoice.total_amount or 0),
        'amount_paid': float(invoice.amount_paid or 0),
        'balance_due': float(invoice.balance_due or 0),
        'notes': invoice.notes,
        'issued_at': invoice.issued_at.isoformat() if invoice.issued_at else None,
        'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
        'items': [serialize_invoice_item(item) for item in invoice.items],
        'payments': [serialize_payment(payment) for payment in invoice.payments],
    }


@bp.route('', methods=['GET'])
@token_required(token_type='access')
def list_invoices():
    filters, sort_by, sort_order = get_filter_and_sort_params()
    page, per_page = get_pagination_params()
    search = parse_search_params()

    invoices, total = service.list_invoices(
        filters=filters,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
    )

    return json_paginated([serialize_invoice(invoice) for invoice in invoices], total, page, per_page)


@bp.route('/<int:invoice_id>', methods=['GET'])
@token_required(token_type='access')
def get_invoice(invoice_id):
    invoice = service.get_invoice(invoice_id)
    if invoice is None:
        return json_error('Invoice not found', error_code='INVOICE_NOT_FOUND', status_code=404)
    return json_success(serialize_invoice(invoice))


@bp.route('', methods=['POST'])
@token_required(token_type='access')
@role_required('manager', 'admin')
def create_invoice():
    payload = require_json()
    try:
        invoice = service.create_invoice(g.jwt_payload, payload, request)
    except ValidationError as exc:
        return json_error(str(exc), error_code='VALIDATION_ERROR', status_code=400)
    except ValueError as exc:
        return json_error(str(exc), error_code='INVOICE_CREATION_FAILED', status_code=400)

    return json_success(serialize_invoice(invoice), status_code=201)


@bp.route('/<int:invoice_id>/payment', methods=['POST'])
@token_required(token_type='access')
def record_invoice_payment(invoice_id):
    payload = require_json()
    try:
        payment = service.record_payment(g.jwt_payload, invoice_id, payload, request)
    except ValidationError as exc:
        return json_error(str(exc), error_code='VALIDATION_ERROR', status_code=400)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            return json_error(message, error_code='INVOICE_NOT_FOUND', status_code=404)
        return json_error(message, error_code='INVOICE_PAYMENT_FAILED', status_code=400)

    return json_success({
        'invoice_id': payment.invoice_id,
        'payment_id': payment.id,
        'amount': float(payment.amount or 0),
        'method': payment.method,
        'reference': payment.reference,
    })


@bp.route('/<int:invoice_id>/cancel', methods=['POST'])
@token_required(token_type='access')
@role_required('manager', 'admin')
def cancel_invoice(invoice_id):
    payload = require_json()
    try:
        invoice = service.cancel_invoice(g.jwt_payload, invoice_id, payload, request)
    except ValidationError as exc:
        return json_error(str(exc), error_code='VALIDATION_ERROR', status_code=400)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            return json_error(message, error_code='INVOICE_NOT_FOUND', status_code=404)
        return json_error(message, error_code='INVOICE_CANCELLATION_FAILED', status_code=400)

    return json_success(serialize_invoice(invoice))
