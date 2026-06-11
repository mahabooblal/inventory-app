from flask_wtf import FlaskForm
from app.forms.product_forms import decimal_filter
from wtforms import DateField, DecimalField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class StockInForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    supplier_id = SelectField('Supplier', coerce=int, validators=[DataRequired()])
    batch_reference = StringField('Batch Reference', validators=[Optional(), Length(max=100)])
    expires_on = DateField('Expiry Date', validators=[Optional()])
    receive_date = DateField('Receive Date', validators=[Optional()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1, max=100000)])
    unit_cost = DecimalField('Unit Cost', places=2, validators=[Optional(), NumberRange(min=0)], default=0, filters=[decimal_filter])
    note = TextAreaField('Notes', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Receive Stock')


class StockAdjustmentForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    adjustment_type = SelectField(
        'Adjustment Type',
        choices=[
            ('damage', 'Damaged Stock'),
            ('loss', 'Lost Stock'),
            ('correction', 'Manual Correction'),
            ('found', 'Found Stock'),
            ('expiry', 'Expired Stock'),
        ],
        validators=[DataRequired()],
    )
    quantity_delta = IntegerField('Quantity Change', validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[DataRequired(), Length(max=255)])
    submit = SubmitField('Request Adjustment')
