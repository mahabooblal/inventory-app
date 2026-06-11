#!/usr/bin/env python
import argparse
import logging
import os
import sys

from app import create_app, db
from app.models import Warehouse
from app.services.reconciliation_service import (
    export_reconciliation_report,
    get_default_warehouse,
    report_reconciliation,
    reconcile_products_with_default_warehouse,
)
from app.services.warehouse_service import get_or_create_default_warehouse


def configure_console_logger():
    logger = logging.getLogger('reconcile_inventory')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def build_parser():
    parser = argparse.ArgumentParser(
        description='Inventory reconciliation and safe warehouse bootstrap utility.',
    )
    parser.add_argument('--product-id', type=int, help='Limit the reconciliation report to a single product.')
    parser.add_argument(
        '--only-mismatch',
        action='store_true',
        default=True,
        help='Show only products with reconciliation mismatches (default).',
    )
    parser.add_argument('--no-only-mismatch', action='store_false', dest='only_mismatch', help='Show all products.')
    parser.add_argument('--report-csv', help='Write the reconciliation report to a CSV file.')
    parser.add_argument('--bootstrap', action='store_true', help='Bootstrap missing warehouse balances into the default warehouse.')
    parser.add_argument('--yes', action='store_true', help='Confirm destructive bootstrap actions.')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    logger = configure_console_logger()

    app = create_app()
    with app.app_context():
        statuses = report_reconciliation(product_id=args.product_id, only_mismatch=args.only_mismatch)
        if not statuses:
            logger.info('No reconciliation mismatches found.')
        else:
            logger.info('Reconciliation report:')
            for row in statuses:
                logger.info(
                    'Product %s (%s) product_qty=%s warehouse_total=%s ledger_net=%s warehouse_diff=%s ledger_diff=%s',
                    row['product_sku'],
                    row['product_name'],
                    row['product_quantity'],
                    row['warehouse_total'],
                    row['ledger_net'],
                    row['difference_warehouse'],
                    row['difference_ledger'],
                )

        if args.report_csv:
            export_reconciliation_report(args.report_csv, statuses)
            logger.info('Wrote reconciliation report to %s', args.report_csv)

        if args.bootstrap:
            if not args.yes:
                logger.error('--bootstrap requires --yes to execute changes. Use dry-run mode without --bootstrap for a report.')
                return 1
            default_warehouse = get_default_warehouse() or get_or_create_default_warehouse()
            if default_warehouse is None:
                logger.error('No warehouse available to bootstrap missing balances.')
                return 1
            logger.info('Bootstrapping missing warehouse balances into %s (%s).', default_warehouse.name, default_warehouse.code)
            actions = reconcile_products_with_default_warehouse(user_id=0, dry_run=False)
            if not actions:
                logger.info('No missing warehouse balances required bootstrapping.')
            else:
                logger.info('Bootstrapped %d product balances into warehouse %s.', len(actions), default_warehouse.name)
                for action in actions:
                    logger.info('Bootstrapped %s (%s): %s units', action['product_name'], action['sku'], action['quantity'])

    return 0


if __name__ == '__main__':
    sys.exit(main())
