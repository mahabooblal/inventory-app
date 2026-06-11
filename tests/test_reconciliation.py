from app import db
from app.models import Warehouse, WarehouseStock
from app.services.reconciliation_service import (
    bootstrap_missing_warehouse_balances,
    product_reconciliation_status,
    report_reconciliation,
)
from app.services.warehouse_service import (
    get_or_create_default_warehouse,
    reverse_transfer,
    request_stock_transfer,
    approve_stock_transfer,
)


def test_reconciliation_detects_missing_warehouse_balance(database, product):
    status = product_reconciliation_status(product.id)

    assert status['product_quantity'] == 5
    assert status['warehouse_total'] == 0
    assert status['ledger_net'] == 0
    assert status['warehouse_mismatch'] is True
    assert status['ledger_mismatch'] is True
    assert status['difference_warehouse'] == 5
    assert status['difference_ledger'] == 5


def test_bootstrap_missing_warehouse_balances_creates_main_warehouse_stock(database, product):
    default_warehouse = get_or_create_default_warehouse()
    assert default_warehouse is not None

    actions = bootstrap_missing_warehouse_balances(dry_run=True)
    assert len(actions) == 1
    assert actions[0]['product_id'] == product.id
    assert actions[0]['quantity'] == 5

    # Dry run should not create warehouse stock records.
    assert WarehouseStock.query.filter_by(product_id=product.id).count() == 0

    # Now perform the actual bootstrap and ensure the balance is created.
    actions = bootstrap_missing_warehouse_balances(dry_run=False)
    assert len(actions) == 1
    db_stock = WarehouseStock.query.filter_by(product_id=product.id, warehouse_id=default_warehouse.id).one()
    assert db_stock.quantity == 5


def test_reverse_transfer_safely_reverts_stock(database, product):
    default_warehouse = get_or_create_default_warehouse()
    other_warehouse = Warehouse(name='Secondary', code='SECOND', address='Secondary location')
    db.session.add(other_warehouse)
    db.session.flush()

    source_balance = WarehouseStock(warehouse_id=default_warehouse.id, product_id=product.id, quantity=5)
    destination_balance = WarehouseStock(warehouse_id=other_warehouse.id, product_id=product.id, quantity=0)
    db.session.add_all([source_balance, destination_balance])
    db.session.commit()

    # Request transfer
    transfer = request_stock_transfer(product.id, default_warehouse.id, other_warehouse.id, 3, user_id=1)
    # Approve transfer to execute it
    transfer = approve_stock_transfer(transfer.id, approver_id=1)

    assert source_balance.quantity == 2
    assert destination_balance.quantity == 3

    reversed_transfer = reverse_transfer(transfer.id, user_id=1)
    assert reversed_transfer.status == 'cancelled'
    assert source_balance.quantity == 5
    assert destination_balance.quantity == 0


def test_report_reconciliation_only_mismatched(database, product):
    results = report_reconciliation()
    assert any(item['product_id'] == product.id for item in results)
