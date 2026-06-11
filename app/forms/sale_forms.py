from flask_wtf import FlaskForm
from app.forms.product_forms import decimal_filter
from wtforms import DecimalField, IntegerField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class SaleForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    customer_id = SelectField('Customer (Optional)', coerce=int, validators=[])
    destination_details = TextAreaField('Destination Details', validators=[Optional(), Length(max=255)])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    selling_price = DecimalField('Selling Price', places=2, validators=[DataRequired(), NumberRange(min=0)], filters=[decimal_filter])
    submit = SubmitField('Save Sale')
