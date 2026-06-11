from app.api.base import Schema, String, Integer, Float


class ProductSchema(Schema):
    id = Integer(required=False)
    name = String(required=True, min_length=1, max_length=255)
    sku = String(required=True, min_length=1, max_length=100)
    barcode = String(required=False, max_length=64)
    description = String(required=False, max_length=1024)
    price = Float(required=True, min_value=0)
    cost_price = Float(required=False, min_value=0)
    quantity = Integer(required=True, min_value=0)
    low_stock_limit = Integer(required=False, min_value=0)
    category_id = Integer(required=False)
    supplier_id = Integer(required=False)
