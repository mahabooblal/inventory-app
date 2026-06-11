from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Optional


class CustomerForm(FlaskForm):
    name = StringField('Customer Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone')
    address = TextAreaField('Address')
    submit = SubmitField('Save Customer')
