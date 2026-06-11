from decimal import Decimal

from app import db
from app.models import Invoice
from app.models.audit_log import log_audit_event
from app.repositories.invoice_repository import InvoiceRepository
from app.services.invoice_service import create_invoice, record_payment


class InvoiceAPIService:
    def __init__(self, repository=None):
        self.repository = repository or InvoiceRepository()

    def list_invoices(self, *, filters=None, search=None, sort_by=None, sort_order=None, page=1, per_page=20):
        return self.repository.list_invoices(
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )

    def get_invoice(self, invoice_id):
        return self.repository.get_by_id(invoice_id)

    def create_invoice(self, user, payload, request_context=None):
        if not isinstance(payload, dict):
            raise ValueError('Request payload must be a JSON object.')

        customer_id = payload.get('customer_id')
        items = payload.get('items')
        notes = payload.get('notes')
        payment_amount = payload.get('payment_amount', 0)
        payment_method = payload.get('payment_method', 'cash')

        if items is None:
            raise ValueError('Invoice items are required.')

        invoice = create_invoice(
            customer_id=customer_id or None,
            items=items,
            user_id=user.get('user_id') or user.get('id'),
            notes=notes,
            payment_amount=payment_amount,
            payment_method=payment_method,
        )
        db.session.commit()
        log_audit_event(user, request_context, 'INVOICE_CREATED', f'invoice:{invoice.id}', 'success')
        return invoice

    def record_payment(self, user, invoice_id, payload, request_context=None):
        if not isinstance(payload, dict):
            raise ValueError('Request payload must be a JSON object.')

        amount = payload.get('amount')
        method = payload.get('method')
        reference = payload.get('reference')

        if amount is None or method is None:
            raise ValueError('Payment amount and method are required.')

        try:
            amount = Decimal(str(amount))
        except (TypeError, ValueError):
            raise ValueError('Invalid payment amount.')

        payment = record_payment(
            invoice_id=invoice_id,
            amount=amount,
            method=method,
            user_id=user.get('user_id') or user.get('id'),
            reference=reference,
        )
        db.session.commit()
        log_audit_event(user, request_context, 'PAYMENT_RECEIVED', f'invoice:{invoice_id}', 'success')
        return payment

    def cancel_invoice(self, user, invoice_id, payload, request_context=None):
        invoice = self.repository.get_by_id(invoice_id)
        if invoice is None:
            raise ValueError('Invoice not found')

        if invoice.status == 'cancelled':
            raise ValueError('Invoice is already cancelled.')
        if invoice.status == 'paid':
            raise ValueError('Paid invoices cannot be cancelled.')

        invoice.status = 'cancelled'
        db.session.add(invoice)
        db.session.commit()
        log_audit_event(user, request_context, 'INVOICE_CANCELLED', f'invoice:{invoice.id}', 'success')
        return invoice


InvoiceService = InvoiceAPIService
