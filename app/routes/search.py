from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models import Product

bp = Blueprint('search', __name__, url_prefix='/search')


@bp.route('/')
@login_required
def global_search():
    query = request.args.get('q', '').strip()
    products = []
    if query:
        term = f'%{query}%'
        products = Product.query.filter((Product.name.ilike(term)) | (Product.sku.ilike(term))).limit(20).all()
    return render_template('search/results.html', title='Search', query=query, products=products)
