from app.api.base import Schema, String, Integer, Float, List, Nested


class PurchaseOrderItemSchema(Schema):
    id = Integer(required=False)
    product_id = Integer(required=True, min_value=1)
    quantity_ordered = Integer(required=True, min_value=1)
    quantity_received = Integer(required=False)
    unit_cost = Float(required=True, min_value=0)


class PurchaseOrderSchema(Schema):
    id = Integer(required=False)
    po_number = String(required=False, min_length=1, max_length=128)
    supplier_id = Integer(required=True, min_value=1)
    status = String(required=False, min_length=1, max_length=64)
    expected_date = String(required=False)
    notes = String(required=False)
    total_amount = Float(required=False, min_value=0)
    items = List(Nested(PurchaseOrderItemSchema), required=False, min_length=0)
