from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class WarehouseForm(FlaskForm):
    name = StringField('Warehouse / Branch Name', validators=[DataRequired(), Length(max=120)])
    code = StringField('Code', validators=[DataRequired(), Length(max=30)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Warehouse')


class StockTransferForm(FlaskForm):
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    source_warehouse_id = SelectField('From Warehouse', coerce=int, validators=[DataRequired()])
    destination_warehouse_id = SelectField('To Warehouse', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    note = TextAreaField('Note', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Transfer Stock')
