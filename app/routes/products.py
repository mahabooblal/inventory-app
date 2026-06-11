import csv
import io
import os
from datetime import date, datetime, time
from decimal import Decimal

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for, abort
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from app.utils.permissions import admin_required, manager_required

from app import db
from app.forms import PriceUpdateForm, ProductForm
from app.models import Category, PriceHistory, Product, Supplier
from app.services.activity_service import log_activity

bp = Blueprint('products', __name__, url_prefix='/products')


def load_product_choices(form):
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()]


def generate_sku(name):
    prefix = ''.join(ch for ch in name.upper() if ch.isalnum())[:4] or 'ITEM'
    next_id = (db.session.query(func.max(Product.id)).scalar() or 0) + 1
    candidate = f'{prefix}-{next_id:05d}'
    suffix = 1
    while Product.query.filter_by(sku=candidate).first():
        suffix += 1
        candidate = f'{prefix}-{next_id + suffix:05d}'
    return candidate


def save_product_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    upload_dir = os.path.join(current_app.static_folder, 'product_images')
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(file_storage.filename)
    stem, ext = os.path.splitext(filename)
    safe_name = f'{stem[:40]}-{date.today().strftime("%Y%m%d")}{ext.lower()}'
    file_storage.save(os.path.join(upload_dir, safe_name))
    return safe_name


@bp.route('/')
@login_required
def list_products():
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', 0, type=int)
    status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)
    query = Product.query.options(joinedload(Product.category), joinedload(Product.supplier))
    if search:
        query = query.filter(or_(Product.name.ilike(f'%{search}%'), Product.sku.ilike(f'%{search}%'), Product.barcode.ilike(f'%{search}%')))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if status == 'active':
        query = query.filter(Product.is_active.is_(True))
    elif status == 'inactive':
        query = query.filter(Product.is_active.is_(False))
    pagination = query.order_by(Product.name).paginate(page=page, per_page=20, error_out=False)
    categories = Category.query.order_by(Category.name).all()
    return render_template('products/list.html', title='Products', products=pagination.items, pagination=pagination, search=search, categories=categories, category_id=category_id, status=status)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
@manager_required
def add_product():
    if Category.query.count() == 0 or Supplier.query.count() == 0:
        flash('Please add at least one category and one supplier before adding products.', 'warning')
        return redirect(url_for('products.list_products'))

    form = ProductForm()
    load_product_choices(form)

    if form.validate_on_submit():
        image_filename = save_product_image(form.image.data)
        product = Product(
            name=form.name.data,
            sku=form.sku.data or generate_sku(form.name.data),
            barcode=form.barcode.data,
            image_filename=image_filename,
            description=form.description.data,
            price=form.price.data,
            cost_price=form.cost_price.data,
            quantity=form.quantity.data,
            low_stock_limit=form.low_stock_limit.data,
            category_id=form.category_id.data,
            supplier_id=form.supplier_id.data,
            is_active=form.is_active.data,
        )
        db.session.add(product)
        db.session.flush()
        log_activity(current_user.id, 'CREATE', 'Product', product.id, f'Added product: {product.name} (SKU: {product.sku})')
        db.session.commit()

        flash('Product added successfully.', 'success')
        return redirect(url_for('products.list_products'))

    return render_template('products/form.html', title='Add Product', form=form)


@bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    form = ProductForm(obj=product)
    load_product_choices(form)

    if form.validate_on_submit():
        old_price = product.price
        image_filename = save_product_image(form.image.data)
        form.populate_obj(product)
        if not product.sku:
            product.sku = generate_sku(product.name)
        if image_filename:
            product.image_filename = image_filename
        log_activity(current_user.id, 'UPDATE', 'Product', product.id, f'Updated product: {product.name} (SKU: {product.sku})')
        if old_price != product.price:
            margin = ((product.price - product.cost_price) / product.price * 100) if product.price else 0
            db.session.add(PriceHistory(product_id=product.id, old_price=old_price, new_price=product.price, effective_date=datetime.combine(date.today(), time.min), approval_note='Updated from product form', margin_percent=margin, created_by=current_user.id))
        db.session.commit()

        flash('Product updated successfully.', 'success')
        return redirect(url_for('products.list_products'))

    return render_template('products/form.html', title='Edit Product', form=form)


@bp.route('/<int:product_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    log_activity(current_user.id, 'DELETE', 'Product', product.id, f'Deleted product: {product.name} (SKU: {product.sku})')
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully.', 'info')
    return redirect(url_for('products.list_products'))


@bp.route('/export.csv')
@login_required
def export_products():
    products = Product.query.options(joinedload(Product.category)).order_by(Product.name).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Product Name', 'SKU', 'Barcode', 'Category', 'Price', 'Cost Price', 'Stock', 'Low Stock Limit', 'Status'])
    for product in products:
        writer.writerow([
            product.name,
            product.sku,
            product.barcode or '',
            product.category.name if product.category else '',
            product.price,
            product.cost_price,
            product.quantity,
            product.low_stock_limit,
            'Active' if product.is_active else 'Inactive',
        ])
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=products.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


@bp.route('/import', methods=['POST'])
@login_required
@manager_required
def import_products():
    upload = request.files.get('csv_file')
    if not upload or not upload.filename:
        flash('Choose a CSV file to import.', 'warning')
        return redirect(url_for('products.list_products'))

    rows = csv.DictReader(io.StringIO(upload.stream.read().decode('utf-8-sig')))
    imported = 0
    default_category = Category.query.order_by(Category.name).first()
    default_supplier = Supplier.query.order_by(Supplier.name).first()
    if not default_category or not default_supplier:
        flash('Add at least one category and supplier before importing products.', 'warning')
        return redirect(url_for('products.list_products'))
    for row in rows:
        name = (row.get('Product Name') or row.get('name') or '').strip()
        if not name:
            continue
        sku = (row.get('SKU') or row.get('sku') or '').strip() or generate_sku(name)
        product = Product.query.filter_by(sku=sku).first() or Product(sku=sku)
        product.name = name
        product.barcode = (row.get('Barcode') or row.get('barcode') or '').strip() or None
        product.price = Decimal(str(row.get('Price') or row.get('price') or 0))
        product.cost_price = Decimal(str(row.get('Cost Price') or row.get('cost_price') or 0))
        product.quantity = int(row.get('Stock') or row.get('quantity') or 0)
        product.low_stock_limit = int(row.get('Low Stock Limit') or row.get('low_stock_limit') or 10)
        product.category_id = product.category_id or default_category.id
        product.supplier_id = product.supplier_id or default_supplier.id
        product.is_active = (row.get('Status') or 'Active').strip().lower() != 'inactive'
        db.session.add(product)
        imported += 1
    db.session.commit()
    flash(f'Imported {imported} products.', 'success')
    return redirect(url_for('products.list_products'))


@bp.route('/prices', methods=['GET', 'POST'])
@login_required
@manager_required
def price_updates():
    form = PriceUpdateForm()
    products = Product.query.order_by(Product.name).all()
    form.product_id.choices = [(p.id, f'{p.name} ({p.sku})') for p in products]
    product_prices = {p.id: float(p.price) for p in products}
    product_costs = {p.id: float(p.cost_price) for p in products}

    if request.method == 'GET':
        form.effective_date.data = date.today()

    if form.validate_on_submit():
        product = db.session.get(Product, form.product_id.data)
        if product is None:
            abort(404)
        old_price = product.price
        product.price = form.new_price.data
        margin = ((product.price - product.cost_price) / product.price * 100) if product.price else 0
        history = PriceHistory(
            product_id=product.id,
            old_price=old_price,
            new_price=product.price,
            effective_date=datetime.combine(form.effective_date.data, time.min),
            approval_note=form.approval_note.data,
            margin_percent=margin,
            created_by=current_user.id,
        )
        db.session.add(history)
        db.session.flush()
        log_activity(current_user.id, 'UPDATE', 'PriceHistory', history.id, f'Updated price for {product.name} from {old_price} to {product.price}')
        db.session.commit()
        flash('Price update saved.', 'success')
        return redirect(url_for('products.price_updates'))

    history = PriceHistory.query.options(joinedload(PriceHistory.product)).order_by(PriceHistory.created_at.desc()).limit(50).all()
    return render_template('products/price_updates.html', title='Daily Price Updates', form=form, history=history, product_prices=product_prices, product_costs=product_costs)
