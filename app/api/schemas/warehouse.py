from app.api.base import Schema, String, Integer, Boolean


class WarehouseSchema(Schema):
    id = Integer(required=False)
    name = String(required=True, min_length=1, max_length=255)
    code = String(required=True, min_length=1, max_length=50)
    address = String(required=False, max_length=255)
    is_active = Boolean(required=False)
