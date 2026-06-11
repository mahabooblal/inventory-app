from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from decimal import Decimal, InvalidOperation
from wtforms import BooleanField, DateField, DecimalField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError
from datetime import date


def decimal_filter(value):
    if value in (None, ''):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return value


class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired()])
    sku = StringField('SKU', validators=[Optional(), Length(max=80)])
    barcode = StringField('Barcode / UPC', validators=[Optional(), Length(max=100)])
    image = FileField('Product Image', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Use JPG, PNG, or WebP images.')])
    description = TextAreaField('Description')
    price = DecimalField('Selling Price', places=2, validators=[DataRequired(), NumberRange(min=0)], filters=[decimal_filter])
    cost_price = DecimalField('Cost Price', places=2, validators=[DataRequired(), NumberRange(min=0)], default=0, filters=[decimal_filter])
    quantity = IntegerField('Opening Quantity', validators=[NumberRange(min=0)], default=0)
    low_stock_limit = IntegerField('Low Stock Limit', validators=[NumberRange(min=0)], default=10)
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    supplier_id = SelectField('Supplier', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active product', default=True)
    submit = SubmitField('Save Product')


class PriceUpdateForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    current_price = DecimalField('Current Selling Price', places=2, validators=[Optional()], filters=[decimal_filter])
    new_price = DecimalField('New Selling Price', places=2, validators=[DataRequired(), NumberRange(min=0)], filters=[decimal_filter])
    effective_date = DateField('Effective Date', validators=[DataRequired()])
    approval_note = TextAreaField('Approval Note', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Update Price')

    def validate_effective_date(self, field):
        if field.data < date.today():
            raise ValidationError('Effective date cannot be in the past.')
