from flask import current_app


def send_low_stock_alert(product_name, quantity, low_stock_limit):
    current_app.logger.info(
        'Low stock alert: %s has %s units left (limit %s).',
        product_name,
        quantity,
        low_stock_limit,
    )
