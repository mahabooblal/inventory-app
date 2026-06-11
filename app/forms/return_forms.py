from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, IntegerField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.forms.product_forms import decimal_filter


class ReturnOrderForm(FlaskForm):
    return_type = SelectField('Return Type', choices=[('customer', 'Customer Return'), ('supplier', 'Supplier Return')], validators=[DataRequired()])
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    customer_id = SelectField('Customer', coerce=int, validators=[Optional()])
    supplier_id = SelectField('Supplier', coerce=int, validators=[Optional()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    refund_amount = DecimalField('Refund Amount', places=2, validators=[Optional(), NumberRange(min=0)], default=0, filters=[decimal_filter])
    restock = BooleanField('Return to sellable stock', default=True)
    reason = TextAreaField('Reason', validators=[DataRequired(), Length(max=255)])
    submit = SubmitField('Process Return')
