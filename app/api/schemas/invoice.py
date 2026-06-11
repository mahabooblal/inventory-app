from app.api.base import Schema, String, Integer, Float, DateTime


class InvoiceSchema(Schema):
    id = Integer(required=False)
    sale_id = Integer(required=True, min_value=1)
    customer_id = Integer(required=True, min_value=1)
    invoice_number = String(required=True, min_length=1, max_length=128)
    status = String(required=True, min_length=1, max_length=64)
    total = Float(required=True, min_value=0)
    due_date = DateTime(required=False)
