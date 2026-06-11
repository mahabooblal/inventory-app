from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.forms.product_forms import decimal_filter


class InvoiceForm(FlaskForm):
    customer_id = SelectField('Customer', coerce=int, validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=255)])
    payment_amount = DecimalField('Initial Payment', places=2, validators=[Optional(), NumberRange(min=0)], default=0, filters=[decimal_filter])
    payment_method = SelectField(
        'Payment Method',
        choices=[
            ('cash', 'Cash'),
            ('card', 'Card'),
            ('upi', 'UPI'),
            ('bank_transfer', 'Bank Transfer'),
            ('credit', 'Credit'),
            ('other', 'Other'),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField('Create Invoice')


class PaymentForm(FlaskForm):
    amount = DecimalField('Amount', places=2, validators=[DataRequired(), NumberRange(min=0.01)], filters=[decimal_filter])
    method = SelectField(
        'Payment Method',
        choices=[
            ('cash', 'Cash'),
            ('card', 'Card'),
            ('upi', 'UPI'),
            ('bank_transfer', 'Bank Transfer'),
            ('credit', 'Credit'),
            ('other', 'Other'),
        ],
        validators=[DataRequired()],
    )
    reference = StringField('Reference', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Record Payment')
