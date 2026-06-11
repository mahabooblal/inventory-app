from sqlalchemy import asc, desc, or_

from app import db
from app.models import Customer, Invoice


class InvoiceRepository:
    SORT_FIELDS = {
        'id': Invoice.id,
        'invoice_number': Invoice.invoice_number,
        'customer_id': Invoice.customer_id,
        'status': Invoice.status,
        'issued_at': Invoice.issued_at,
        'created_at': Invoice.created_at,
    }

    def list_invoices(self, filters=None, search=None, sort_by=None, sort_order='asc', page=1, per_page=20):
        filters = filters or {}
        query = db.session.query(Invoice).outerjoin(Customer)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    Invoice.invoice_number.ilike(search_pattern),
                    Invoice.status.ilike(search_pattern),
                    Customer.name.ilike(search_pattern),
                )
            )

        if filters.get('customer_id'):
            query = query.filter(Invoice.customer_id == filters['customer_id'])

        if filters.get('status'):
            query = query.filter(Invoice.status == filters['status'])

        if filters.get('invoice_number'):
            query = query.filter(Invoice.invoice_number == filters['invoice_number'])

        total = query.count()
        sort_column = self.SORT_FIELDS.get(sort_by, Invoice.created_at)
        order_by = asc(sort_column) if sort_order == 'asc' else desc(sort_column)
        invoices = query.order_by(order_by).offset((page - 1) * per_page).limit(per_page).all()
        return invoices, total

    def get_by_id(self, invoice_id):
        return db.session.get(Invoice, invoice_id)
