from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.forms import SaleForm
from app.models import Customer, Product, Sale
from app.services.activity_service import log_activity
from app.services.email_service import send_low_stock_alert
from app.services.inventory_service import record_sale
from app.services.notification_service import notify_role_users

bp = Blueprint('sales', __name__, url_prefix='/sales')


@bp.route('/new', methods=['GET', 'POST'])
@bp.route('/outgoing', methods=['GET', 'POST'])
@login_required
def create_sale():
    form = SaleForm()
    products = Product.query.order_by(Product.name).all()
    form.product_id.choices = [(p.id, f'{p.name} - Stock: {p.quantity}') for p in products]
    product_prices = {p.id: float(p.price) for p in products}
    product_meta = {p.id: {'quantity': p.quantity, 'price': float(p.price), 'low_stock_limit': p.low_stock_limit} for p in products}
    form.customer_id.choices = [(0, 'Walk-in Customer')] + [(c.id, c.name) for c in Customer.query.order_by(Customer.name).all()]

    if form.validate_on_submit():
        try:
            customer_id = form.customer_id.data if form.customer_id.data != 0 else None
            sale = record_sale(
                form.product_id.data,
                form.quantity.data,
                form.selling_price.data,
                current_user.id,
                customer_id,
                destination_details=form.destination_details.data,
                commit=False,
            )

            product = db.session.get(Product, form.product_id.data)
            if product is None:
                raise ValueError('Product not found')
            customer = db.session.get(Customer, customer_id) if customer_id else None
            customer_name = customer.name if customer else 'Walk-in Customer'
            log_activity(
                current_user.id,
                'CREATE',
                'Sale',
                sale.id,
                f'Sold {form.quantity.data} x {product.name} to {customer_name} for ₹{form.selling_price.data * form.quantity.data:.2f}',
            )
            notify_role_users(
                ['admin', 'manager'],
                f'{current_user.username} sold {form.quantity.data} x {product.name} to {customer_name}.',
                'success',
            )
            if product.quantity <= product.low_stock_limit:
                notify_role_users(
                    ['admin', 'manager'],
                    f'Low stock: {product.name} has {product.quantity} units left.',
                    'warning',
                )
            db.session.commit()

            if product.quantity <= product.low_stock_limit:
                send_low_stock_alert(product.name, product.quantity, product.low_stock_limit)

            flash('Sale saved and stock quantity updated.', 'success')
            return redirect(url_for('sales.create_sale'))
        except ValueError as error:
            flash(str(error), 'danger')

    sales = Sale.query.order_by(Sale.sale_date.desc()).limit(20).all()
    return render_template('sales/create_sale.html', title='Outgoing Stock', form=form, sales=sales, product_prices=product_prices, product_meta=product_meta)


@bp.route('/')
@login_required
def list_sales():
    """Paginated sales listing for admin/manager."""
    page = request.args.get('page', 1, type=int)
    pagination = Sale.query.order_by(Sale.sale_date.desc()).paginate(page=page, per_page=25, error_out=False)
    return render_template('sales/list.html', title='Sales', sales=pagination.items, pagination=pagination)
