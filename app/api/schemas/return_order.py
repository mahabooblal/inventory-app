from app.api.base import Schema, String, Integer, Float, Boolean, DateTime


class ReturnOrderSchema(Schema):
    id = Integer(required=False)
    return_number = String(required=False)
    return_type = String(required=True, min_length=1, max_length=20)
    product_id = Integer(required=True, min_value=1)
    customer_id = Integer(required=False, min_value=1)
    supplier_id = Integer(required=False, min_value=1)
    quantity = Integer(required=True, min_value=1)
    refund_amount = Float(required=False, min_value=0)
    restock = Boolean(required=False)
    reason = String(required=True, min_length=1, max_length=255)
    status = String(required=False)
    rejection_reason = String(required=False)
    cancellation_reason = String(required=False)
    approved_by = Integer(required=False)
    approved_at = DateTime(required=False)
    created_by = Integer(required=False)
    created_at = DateTime(required=False)
