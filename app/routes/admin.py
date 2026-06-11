from flask import Blueprint, flash, redirect, render_template, request, url_for, abort
from flask_login import current_user, login_required

from app import db
from app.forms import CreateUserForm
from app.models import User
from app.services.activity_service import log_activity
from app.utils.permissions import roles_required

bp = Blueprint('admin', __name__, url_prefix='/admin')

from app.routes.backup_admin import bp as backup_admin_bp

@bp.route('/users')
@login_required
@roles_required('admin')
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', title='Users', users=all_users)


@bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def new_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        log_activity(current_user.id, 'CREATE', 'User', user.id, f'Created user: {user.username}')
        db.session.commit()
        flash('User created successfully.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', title='Create User', form=form)


@bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@roles_required('admin')
def toggle_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'warning')
        return redirect(url_for('admin.users'))
    user.is_active = not user.is_active
    log_activity(current_user.id, 'UPDATE', 'User', user.id, f'Toggled user active state: {user.username}')
    db.session.commit()
    flash('User status updated.', 'success')
    return redirect(url_for('admin.users'))


@bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
@roles_required('admin')
def update_role(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    role = request.form.get('role')
    if role in {'admin', 'manager', 'staff'}:
        user.role = role
        log_activity(current_user.id, 'UPDATE', 'User', user.id, f'Changed role for: {user.username}')
        db.session.commit()
        flash('User role updated.', 'success')
    return redirect(url_for('admin.users'))
