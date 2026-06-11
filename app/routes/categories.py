from flask import Blueprint, flash, redirect, render_template, url_for, abort
from flask_login import current_user, login_required

from app import db
from app.forms import CategoryForm
from app.models import Category
from app.services.activity_service import log_activity
from app.utils.permissions import admin_required, manager_required

bp = Blueprint('categories', __name__, url_prefix='/categories')


@bp.route('/')
@login_required
def list_categories():
    from flask import request
    page = request.args.get('page', 1, type=int)
    pagination = Category.query.order_by(Category.name).paginate(page=page, per_page=20, error_out=False)
    return render_template('categories/list.html', title='Categories', categories=pagination.items, pagination=pagination)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
@manager_required
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data, description=form.description.data)
        db.session.add(category)
        db.session.flush()
        log_activity(current_user.id, 'CREATE', 'Category', category.id, f'Added category: {category.name}')
        db.session.commit()

        flash('Category saved successfully.', 'success')
        return redirect(url_for('categories.list_categories'))
    return render_template('categories/form.html', title='Add Category', form=form)


@bp.route('/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_category(category_id):
    category = db.session.get(Category, category_id)
    if category is None:
        abort(404)
    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        form.populate_obj(category)
        log_activity(current_user.id, 'UPDATE', 'Category', category.id, f'Updated category: {category.name}')
        db.session.commit()

        flash('Category updated successfully.', 'success')
        return redirect(url_for('categories.list_categories'))
    return render_template('categories/form.html', title='Edit Category', form=form)


@bp.route('/<int:category_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    category = db.session.get(Category, category_id)
    if category is None:
        abort(404)
    if category.products.count() > 0:
        flash('Cannot delete a category that is linked to products.', 'warning')
        return redirect(url_for('categories.list_categories'))

    log_activity(current_user.id, 'DELETE', 'Category', category.id, f'Deleted category: {category.name}')
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully.', 'info')
    return redirect(url_for('categories.list_categories'))
