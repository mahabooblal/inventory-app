from flask_wtf import FlaskForm
from wtforms import BooleanField, FileField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class ProfileEditForm(FlaskForm):
    """Form for editing user profile information."""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=30)])
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Save Profile')


class ChangePasswordForm(FlaskForm):
    """Form for changing user password with optional current password verification."""
    current_password = PasswordField('Current Password', validators=[Optional()])
    new_password = PasswordField(
        'New Password',
        validators=[DataRequired(), Length(min=8, message='Password must be at least 8 characters long.')]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('new_password', message='Passwords must match.')]
    )
    submit = SubmitField('Change Password')


class ProfileImageForm(FlaskForm):
    """Form for uploading a profile image."""
    profile_image = FileField('Profile Image')
    submit = SubmitField('Upload')


class UserPreferencesForm(FlaskForm):
    """Form for managing user preferences and settings."""
    preferred_theme = SelectField(
        'Theme Preference',
        choices=[('light', 'Light'), ('dark', 'Dark'), ('system', 'System (Auto)')],
        validators=[DataRequired()]
    )
    dashboard_density = SelectField(
        'Dashboard Density',
        choices=[('comfortable', 'Comfortable'), ('compact', 'Compact')],
        validators=[DataRequired()]
    )
    email_notifications = BooleanField('Enable Email Notifications')
    submit = SubmitField('Save Preferences')
