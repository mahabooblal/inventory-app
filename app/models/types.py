from app import db


class UTCDateTime(db.TypeDecorator):
    impl = db.DateTime(timezone=True)
    cache_ok = True
