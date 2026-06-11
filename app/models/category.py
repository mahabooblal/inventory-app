from app import db
from app.models.types import UTCDateTime
from app.utils.datetime import utc_now


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(UTCDateTime(), default=utc_now)

    products = db.relationship('Product', back_populates='category', lazy='dynamic')
