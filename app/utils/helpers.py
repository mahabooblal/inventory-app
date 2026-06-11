from decimal import Decimal, InvalidOperation


def money(value):
    """Format money consistently for templates and exports."""
    try:
        amount = Decimal(value or 0)
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal('0')
    return f'₹{amount:.2f}'
