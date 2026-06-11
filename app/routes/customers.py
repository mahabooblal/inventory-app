from flask import Blueprint, render_template
from flask_login import login_required

from app.models import Customer

bp = Blueprint('customers', __name__, url_prefix='/customers')


@bp.route('/')
@login_required
def list_customers():
    customers = Customer.query.order_by(Customer.name).all()
    return render_template('customers/list.html', title='Customers', customers=customers)
