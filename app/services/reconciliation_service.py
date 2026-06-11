from app import db
from app.models import Product, StockMovement, Warehouse, WarehouseStock
from app.services.activity_service import log_activity
from app.utils.datetime import utc_now


def get_product_warehouse_total(product_id):
    return int(
        db.session.query(db.func.coalesce(db.func.sum(WarehouseStock.quantity), 0))
        .filter(WarehouseStock.product_id == product_id)
        .scalar() or 0
    )


def get_product_ledger_net(product_id):
    return int(
        db.session.query(db.func.coalesce(db.func.sum(StockMovement.quantity), 0))
        .filter(StockMovement.product_id == product_id)
        .scalar() or 0
    )


def product_reconciliation_status(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        raise ValueError('Product not found')

    warehouse_total = get_product_warehouse_total(product_id)
    ledger_net = get_product_ledger_net(product_id)
    return {
        'product_id': product.id,
        'product_name': product.name,
        'product_sku': product.sku,
        'product_quantity': int(product.quantity),
        'warehouse_total': warehouse_total,
        'ledger_net': ledger_net,
        'warehouse_mismatch': int(product.quantity) != warehouse_total,
        'ledger_mismatch': int(product.quantity) != ledger_net,
        'difference_warehouse': int(product.quantity) - warehouse_total,
        'difference_ledger': int(product.quantity) - ledger_net,
    }


def find_mismatched_products(only_mismatch=True):
    query = Product.query.order_by(Product.id)
    results = []
    for product in query.all():
        status = product_reconciliation_status(product.id)
        if not only_mismatch or status['warehouse_mismatch'] or status['ledger_mismatch']:
            results.append(status)
    return results


def get_default_warehouse():
    warehouse = Warehouse.query.filter_by(code='MAIN').first()
    if warehouse:
        return warehouse
    return Warehouse.query.order_by(Warehouse.id).first()


def report_reconciliation(product_id=None, only_mismatch=True):
    if product_id is not None:
        return [product_reconciliation_status(product_id)]
    return find_mismatched_products(only_mismatch=only_mismatch)


def bootstrap_missing_warehouse_balances(user_id=None, dry_run=True):
    default_warehouse = get_default_warehouse()
    if default_warehouse is None:
        raise ValueError('No warehouse available to bootstrap missing balances.')

    actions = []
    for product in Product.query.order_by(Product.id).all():
        warehouse_total = get_product_warehouse_total(product.id)
        if product.quantity <= 0 or warehouse_total != 0:
            continue

        actions.append({
            'product_id': product.id,
            'product_name': product.name,
            'sku': product.sku,
            'quantity': int(product.quantity),
            'warehouse_id': default_warehouse.id,
            'warehouse_name': default_warehouse.name,
        })
        if not dry_run:
            balance = WarehouseStock(
                warehouse_id=default_warehouse.id,
                product_id=product.id,
                quantity=int(product.quantity),
            )
            db.session.add(balance)
            db.session.flush()
            log_activity(
                user_id or 0,
                'RECONCILE',
                'WarehouseStock',
                balance.id,
                f'Bootstrapped {balance.quantity} units for {product.name} into warehouse {default_warehouse.name}',
            )

    return actions


def format_reconciliation_summary(status_list):
    lines = []
    for status in status_list:
        lines.append(
            f"Product {status['product_sku']} ({status['product_name']}): "
            f"product_qty={status['product_quantity']}, "
            f"warehouse_sum={status['warehouse_total']}, "
            f"ledger_net={status['ledger_net']}, "
            f"warehouse_diff={status['difference_warehouse']}, "
            f"ledger_diff={status['difference_ledger']}"
        )
    return lines


def export_reconciliation_report(path, statuses):
    import csv

    fieldnames = [
        'product_id',
        'product_sku',
        'product_name',
        'product_quantity',
        'warehouse_total',
        'ledger_net',
        'difference_warehouse',
        'difference_ledger',
        'warehouse_mismatch',
        'ledger_mismatch',
    ]
    with open(path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for status in statuses:
            writer.writerow({k: status[k] for k in fieldnames})


def reconcile_products_with_default_warehouse(user_id=None, dry_run=True):
    actions = bootstrap_missing_warehouse_balances(user_id=user_id, dry_run=dry_run)
    if not dry_run and actions:
        db.session.commit()
    return actions
