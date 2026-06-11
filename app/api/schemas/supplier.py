from app.api.base import Schema, String, Integer, Email


class SupplierSchema(Schema):
    id = Integer(required=False)
    name = String(required=True, min_length=1, max_length=255)
    email = Email(required=True, max_length=255)
    phone = String(required=False, max_length=50)
    address = String(required=False, max_length=512)
