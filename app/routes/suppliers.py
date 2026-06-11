from flask import Blueprint, flash, redirect, render_template, url_for, abort
from flask_login import current_user, login_required

from app import db
from app.forms import SupplierForm
from app.models import Supplier
from app.services.activity_service import log_activity
from app.utils.permissions import admin_required, manager_required

bp = Blueprint('suppliers', __name__, url_prefix='/suppliers')


@bp.route('/')
@login_required
def list_suppliers():
    from flask import request
    page = request.args.get('page', 1, type=int)
    pagination = Supplier.query.order_by(Supplier.name).paginate(page=page, per_page=20, error_out=False)
    return render_template('suppliers/list.html', title='Suppliers', suppliers=pagination.items, pagination=pagination)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
@manager_required
def add_supplier():
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
        )
        db.session.add(supplier)
        db.session.flush()
        log_activity(current_user.id, 'CREATE', 'Supplier', supplier.id, f'Added supplier: {supplier.name}')
        db.session.commit()

        flash('Supplier saved successfully.', 'success')
        return redirect(url_for('suppliers.list_suppliers'))
    return render_template('suppliers/form.html', title='Add Supplier', form=form)


@bp.route('/<int:supplier_id>/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_supplier(supplier_id):
    supplier = db.session.get(Supplier, supplier_id)
    if supplier is None:
        abort(404)
    form = SupplierForm(obj=supplier)
    if form.validate_on_submit():
        form.populate_obj(supplier)
        log_activity(current_user.id, 'UPDATE', 'Supplier', supplier.id, f'Updated supplier: {supplier.name}')
        db.session.commit()

        flash('Supplier updated successfully.', 'success')
        return redirect(url_for('suppliers.list_suppliers'))
    return render_template('suppliers/form.html', title='Edit Supplier', form=form)


@bp.route('/<int:supplier_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_supplier(supplier_id):
    supplier = db.session.get(Supplier, supplier_id)
    if supplier is None:
        abort(404)
    if supplier.products.count() > 0:
        flash('Cannot delete a supplier that is linked to products.', 'warning')
        return redirect(url_for('suppliers.list_suppliers'))

    log_activity(current_user.id, 'DELETE', 'Supplier', supplier.id, f'Deleted supplier: {supplier.name}')
    db.session.delete(supplier)
    db.session.commit()
    flash('Supplier deleted successfully.', 'info')
    return redirect(url_for('suppliers.list_suppliers'))
