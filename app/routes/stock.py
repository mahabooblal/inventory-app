from datetime import date, datetime, time

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app import db
from app.forms import StockInForm
from app.models import Product, StockIn, Supplier
from app.services.inventory_service import add_stock
from app.services.activity_service import log_activity
from app.services.notification_service import notify_role_users

bp = Blueprint('stock', __name__, url_prefix='/stock')


@bp.route('/out')
@login_required
def stock_out():
    return redirect(url_for('sales.create_sale'))


@bp.route('/in', methods=['GET', 'POST'])
@login_required
def stock_in():
    form = StockInForm()
    form.product_id.choices = [(p.id, f'{p.name} ({p.sku})') for p in Product.query.order_by(Product.name).all()]
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()]
    products = Product.query.order_by(Product.name).all()
    product_meta = {
        p.id: {
            'name': p.name,
            'quantity': p.quantity,
            'low_stock_limit': p.low_stock_limit,
            'cost_price': float(p.cost_price),
        }
        for p in products
    }

    if not form.receive_date.data:
        form.receive_date.data = date.today()

    if form.validate_on_submit():
        stock_entry = add_stock(
            form.product_id.data,
            form.supplier_id.data,
            form.quantity.data,
            form.note.data,
            current_user.id,
            batch_reference=form.batch_reference.data,
            expires_on=form.expires_on.data,
            receive_date=datetime.combine(form.receive_date.data or date.today(), time.min),
            unit_cost=form.unit_cost.data or 0,
            commit=False,
        )

        product = db.session.get(Product, form.product_id.data)
        if product is None:
            raise ValueError('Product not found')
        supplier = db.session.get(Supplier, form.supplier_id.data)
        if supplier is None:
            raise ValueError('Supplier not found')
        log_activity(
            current_user.id,
            'CREATE',
            'StockIn',
            stock_entry.id,
            f'Added {form.quantity.data} units of {product.name} from {supplier.name}',
        )
        if product.quantity <= product.low_stock_limit:
            notify_role_users(
                ['admin', 'manager'],
                f'Low stock: {product.name} has {product.quantity} units left after stock update.',
                'warning',
            )
        db.session.commit()

        flash('Stock added and product quantity updated.', 'success')
        return redirect(url_for('stock.stock_in'))

    entries = StockIn.query.order_by(StockIn.created_at.desc()).limit(20).all()
    return render_template('stock/stock_in.html', title='Incoming Stock', form=form, entries=entries, product_meta=product_meta)
