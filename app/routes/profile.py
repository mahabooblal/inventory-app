import logging
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.forms import ChangePasswordForm, ProfileEditForm, ProfileImageForm, UserPreferencesForm

logger = logging.getLogger(__name__)

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


@profile_bp.route('/')
@login_required
def profile():
    """Display the current user's profile."""
    try:
        return render_template('profile/profile.html', title='My Profile')
    except Exception as e:
        logger.exception('Error rendering profile page')
        flash('Something went wrong. Please try again later.', 'danger')
        return redirect(url_for('dashboard.index'))


@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit the current user's profile."""
    try:
        form = ProfileEditForm(obj=current_user)
        if form.validate_on_submit():
            # Only update safe fields
            current_user.username = form.username.data
            current_user.email = form.email.data
            current_user.phone = form.phone.data
            current_user.bio = form.bio.data
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('profile.profile'))
        return render_template('profile/form.html', title='Edit Profile', form=form)
    except Exception as e:
        logger.exception('Error in edit_profile')
        flash('Something went wrong. Please try again later.', 'danger')
        return redirect(url_for('profile.profile'))


@profile_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Manage user preferences."""
    try:
        form = UserPreferencesForm(obj=current_user)
        if form.validate_on_submit():
            # Safely update preferences
            current_user.preferred_theme = form.preferred_theme.data
            current_user.dashboard_density = form.dashboard_density.data
            current_user.email_notifications = form.email_notifications.data
            db.session.commit()
            flash('Preferences updated successfully.', 'success')
            return redirect(url_for('profile.settings'))
        return render_template('profile/form.html', title='Preferences', form=form)
    except Exception as e:
        logger.exception('Error in settings')
        flash('Something went wrong. Please try again later.', 'danger')
        return redirect(url_for('profile.profile'))


@profile_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change the current user's password."""
    try:
        form = ChangePasswordForm()
        if form.validate_on_submit():
            # Verify current password if provided
            if form.current_password.data:
                if not current_user.check_password(form.current_password.data):
                    form.current_password.errors.append('Incorrect current password.')
                    return render_template('profile/form.html', title='Change Password', form=form)
            
            # Set new password (don't use populate_obj for password fields)
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Password changed successfully.', 'success')
            return redirect(url_for('profile.profile'))
        return render_template('profile/form.html', title='Change Password', form=form)
    except Exception as e:
        logger.exception('Error in change_password')
        flash('Something went wrong. Please try again later.', 'danger')
        return redirect(url_for('profile.profile'))


@profile_bp.route('/theme', methods=['POST'])
@login_required
def theme():
    """Update the user's theme preference."""
    try:
        selected = request.form.get('theme', '').strip()
        if selected in {'light', 'dark', 'system'}:
            current_user.preferred_theme = selected
            db.session.commit()
            logger.info(f'User {current_user.id} changed theme to {selected}')
    except Exception as e:
        logger.exception('Error updating theme')
        flash('Could not update theme preference.', 'danger')
    
    return redirect(request.referrer or url_for('dashboard.index'))
