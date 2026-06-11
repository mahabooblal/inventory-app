from app.api.base import Schema, String, Integer, Float, DateTime


class SaleSchema(Schema):
    id = Integer(required=False)
    customer_id = Integer(required=True, min_value=1)
    status = String(required=True, min_length=1, max_length=64)
    total = Float(required=True, min_value=0)
    sale_date = DateTime(required=False)
