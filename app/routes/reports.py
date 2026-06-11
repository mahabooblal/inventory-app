from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.forms import ReportFilterForm
from app.services import export_service
from app.services.report_service import (
    low_stock_products,
    sales_between,
    sales_total,
    inventory_report,
    product_sales_between,
    category_sales_between,
    customer_sales_between,
    profit_loss_between,
    movement_summary_between,
)
from app.models import Product, Category, Customer
from app.utils.permissions import roles_required

bp = Blueprint('reports', __name__, url_prefix='/reports')


@bp.route('/', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'manager')
def index():
    form = ReportFilterForm()
    # populate dynamic choices
    form.product_id.choices = [(0, 'All Products')] + [(p.id, p.name) for p in Product.query.order_by(Product.name).all()]
    form.category_id.choices = [(0, 'All Categories')] + [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    form.customer_id.choices = [(0, 'All Customers')] + [(c.id, c.name) for c in Customer.query.order_by(Customer.name).all()]

    if request.method == 'GET':
        form.from_date.data = date.today()
        form.to_date.data = date.today()

    sales = []
    low_stock = []
    inventory = []
    total = 0
    summary = None
    movement = None

    if form.validate_on_submit():
        rtype = form.report_type.data
        if rtype == 'low_stock':
            low_stock = low_stock_products()
        elif rtype == 'inventory':
            inventory = inventory_report()
        elif rtype == 'product_sales' and form.product_id.data:
            pid = form.product_id.data if form.product_id.data != 0 else None
            if pid:
                sales = product_sales_between(pid, form.from_date.data, form.to_date.data)
                total = sales_total(sales)
            else:
                sales = sales_between(form.from_date.data, form.to_date.data)
                total = sales_total(sales)
        elif rtype == 'category_sales' and form.category_id.data:
            cid = form.category_id.data if form.category_id.data != 0 else None
            if cid:
                sales = category_sales_between(cid, form.from_date.data, form.to_date.data)
                total = sales_total(sales)
            else:
                sales = sales_between(form.from_date.data, form.to_date.data)
                total = sales_total(sales)
        elif rtype == 'customer_sales' and form.customer_id.data:
            cuid = form.customer_id.data if form.customer_id.data != 0 else None
            if cuid:
                sales = customer_sales_between(cuid, form.from_date.data, form.to_date.data)
                total = sales_total(sales)
            else:
                sales = sales_between(form.from_date.data, form.to_date.data)
                total = sales_total(sales)
        elif rtype == 'profit_loss':
            summary = profit_loss_between(form.from_date.data, form.to_date.data)
        elif rtype in {'movement', 'incoming_outgoing', 'net_stock'}:
            pid = form.product_id.data if form.product_id.data != 0 else None
            movement = movement_summary_between(form.from_date.data, form.to_date.data, pid)
        else:
            sales = sales_between(form.from_date.data, form.to_date.data)
            total = sales_total(sales)

    return render_template('reports/reports.html', title='Reports', form=form, sales=sales, low_stock=low_stock, inventory=inventory, total=total, summary=summary, movement=movement)


@bp.route('/export/<report_type>/<file_type>')
@login_required
@roles_required('admin', 'manager')
def export_report(report_type, file_type):
    # parse params
    try:
        from_date = date.fromisoformat(request.args.get('from_date', str(date.today())))
        to_date = date.fromisoformat(request.args.get('to_date', str(date.today())))
        pid = int(request.args.get('product_id', 0)) if request.args.get('product_id') else 0
        cid = int(request.args.get('category_id', 0)) if request.args.get('category_id') else 0
        cuid = int(request.args.get('customer_id', 0)) if request.args.get('customer_id') else 0
    except ValueError:
        flash('Invalid report filter values.', 'danger')
        return redirect(url_for('reports.index'))

    if report_type == 'sales':
        sales = sales_between(from_date, to_date)
        total = sales_total(sales)
        if file_type == 'pdf':
            return export_service.sales_pdf_response(sales, total)
        if file_type == 'xlsx':
            return export_service.sales_excel_response(sales)
        return export_service.sales_csv_response(sales)
    if report_type in {'movement', 'incoming_outgoing', 'net_stock'}:
        product_id = pid if pid else None
        summary = movement_summary_between(from_date, to_date, product_id)
        if file_type == 'pdf':
            return export_service.movement_pdf_response(summary)
        if file_type == 'xlsx':
            return export_service.movement_excel_response(summary)
        return export_service.movement_excel_response(summary)
    if report_type == 'product_sales':
        if pid:
            sales = product_sales_between(pid, from_date, to_date)
        else:
            sales = sales_between(from_date, to_date)
        total = sales_total(sales)
        if file_type == 'pdf':
            return export_service.sales_pdf_response(sales, total)
        if file_type == 'xlsx':
            return export_service.sales_excel_response(sales)
        return export_service.sales_csv_response(sales)
    if report_type == 'category_sales':
        if cid:
            sales = category_sales_between(cid, from_date, to_date)
        else:
            sales = sales_between(from_date, to_date)
        total = sales_total(sales)
        if file_type == 'pdf':
            return export_service.sales_pdf_response(sales, total)
        if file_type == 'xlsx':
            return export_service.sales_excel_response(sales)
        return export_service.sales_csv_response(sales)
    if report_type == 'customer_sales':
        if cuid:
            sales = customer_sales_between(cuid, from_date, to_date)
        else:
            sales = sales_between(from_date, to_date)
        total = sales_total(sales)
        if file_type == 'pdf':
            return export_service.sales_pdf_response(sales, total)
        if file_type == 'xlsx':
            return export_service.sales_excel_response(sales)
        return export_service.sales_csv_response(sales)
    if report_type == 'inventory':
        rows = inventory_report()
        totals = {'value': sum(r['total_value'] for r in rows)}
        if file_type == 'pdf':
            return export_service.inventory_pdf_response(rows, totals)
        if file_type == 'xlsx':
            return export_service.inventory_excel_response(rows)
        return export_service.inventory_csv_response(rows)
    if report_type == 'low_stock':
        rows = low_stock_products()
        if file_type == 'pdf':
            rows_for_pdf = [{ 'name': p.name, 'sku': p.sku, 'quantity': p.quantity, 'total_value': 0 } for p in rows]
            return export_service.inventory_pdf_response(rows_for_pdf, totals=None)
        return export_service.inventory_csv_response([{ 'name': p.name, 'sku': p.sku, 'quantity': p.quantity, 'price': 0.0, 'cost_price': 0.0, 'total_value': 0.0, 'total_cost': 0.0 } for p in rows])
    if report_type == 'profit_loss':
        summary = profit_loss_between(from_date, to_date)
        if file_type == 'pdf':
            return export_service.profit_pdf_response(summary)
        return export_service.profit_csv_response(summary)

    # default
    sales = sales_between(from_date, to_date)
    total = sales_total(sales)
    if file_type == 'pdf':
        return export_service.sales_pdf_response(sales, total)
    if file_type == 'xlsx':
        return export_service.sales_excel_response(sales)
    return export_service.sales_csv_response(sales)
