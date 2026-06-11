from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField
from wtforms.validators import DataRequired


class ReportFilterForm(FlaskForm):
    report_type = SelectField(
        'Report Type',
        choices=[
            ('sales', 'Sales Report'),
            ('movement', 'Inventory Movement'),
            ('incoming_outgoing', 'Incoming vs Outgoing Summary'),
            ('net_stock', 'Net Stock Movement'),
            ('product_sales', 'Product-wise Sales'),
            ('category_sales', 'Category-wise Sales'),
            ('customer_sales', 'Customer-wise Sales'),
            ('inventory', 'Inventory Report'),
            ('low_stock', 'Low Stock Report'),
            ('profit_loss', 'Profit / Loss Summary'),
        ],
    )
    from_date = DateField('From Date', validators=[DataRequired()])
    to_date = DateField('To Date', validators=[DataRequired()])
    product_id = SelectField('Product', choices=[], coerce=int)
    category_id = SelectField('Category', choices=[], coerce=int)
    customer_id = SelectField('Customer', choices=[], coerce=int)
    submit = SubmitField('Filter')
