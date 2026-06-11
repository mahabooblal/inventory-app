from flask_wtf import FlaskForm
from wtforms import EmailField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional


class SupplierForm(FlaskForm):
    name = StringField('Supplier Name', validators=[DataRequired()])
    email = EmailField('Email', validators=[Optional()])
    phone = StringField('Phone')
    address = TextAreaField('Address')
    submit = SubmitField('Save Supplier')
