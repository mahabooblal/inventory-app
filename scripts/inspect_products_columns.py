from app import create_app, db

app = create_app()
with app.app_context():
    inspector = db.inspect(db.engine)
    if not inspector.has_table('products'):
        print('NO_TABLE')
    else:
        cols = [c['name'] for c in inspector.get_columns('products')]
        print('COLUMNS:' + ','.join(cols))
