from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(30))
    address = db.Column(db.String(255))
    created_at = db.Column(UTCDateTime(), default=utc_now)

    sales = db.relationship('Sale', back_populates='customer', lazy='dynamic')
