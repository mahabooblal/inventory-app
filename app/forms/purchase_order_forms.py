from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class PurchaseOrderForm(FlaskForm):
    supplier_id = SelectField('Supplier', coerce=int, validators=[DataRequired()])
    expected_date = DateField('Expected Date', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Create Purchase Order')


class PurchaseOrderReceiveForm(FlaskForm):
    batch_reference = StringField('Batch Reference', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Receive Selected Items')
