"""API Package - Blueprint-based versioned API structure."""

from app.api.base import register_api_error_handlers

API_VERSION = 'v1'


def init_api(app):
    """Initialize API blueprints with Flask app."""

    from app.api.auth import bp as auth_bp
    from app.api.docs import bp as docs_bp
    from app.api.inventory import bp as inventory_bp
    from app.api.products import bp as products_bp
    from app.api.system import bp as system_bp
    from app.api.warehouses import bp as warehouses_bp
    from app.api.suppliers import bp as suppliers_bp
    from app.api.purchase_orders import bp as purchase_orders_bp
    from app.api.sales import bp as sales_bp
    from app.api.invoices import bp as invoices_bp
    from app.api.returns import bp as returns_bp

    app.register_blueprint(docs_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(warehouses_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(purchase_orders_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(returns_bp)

    register_api_error_handlers(app)
    app.logger.info('API blueprints registered.')
