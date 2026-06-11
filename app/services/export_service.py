import csv
import io

from flask import make_response
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def sales_csv_response(sales):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Product', 'Quantity', 'Selling Price', 'Total'])

    for sale in sales:
        writer.writerow([
            sale.sale_date.strftime('%Y-%m-%d %H:%M'),
            sale.product.name,
            sale.quantity,
            sale.selling_price,
            sale.total_amount,
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=sales_report.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


def sales_pdf_response(sales, total):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle('Sales Report')
    pdf.drawString(40, 750, 'Sales Report')
    pdf.drawString(40, 730, f'Total Sales Amount: {total:.2f}')

    y = 700
    for sale in sales:
        line = f'{sale.sale_date:%Y-%m-%d} | {sale.product.name} | Qty: {sale.quantity} | Total: {sale.total_amount:.2f}'
        pdf.drawString(40, y, line[:100])
        y -= 20
        if y < 60:
            pdf.showPage()
            y = 750

    pdf.save()
    buffer.seek(0)

    response = make_response(buffer.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=sales_report.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response


def inventory_csv_response(report_rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Product', 'SKU', 'Quantity', 'Price', 'Cost Price', 'Total Value', 'Total Cost'])

    for row in report_rows:
        writer.writerow([
            row['name'],
            row['sku'],
            row['quantity'],
            row['price'],
            row['cost_price'],
            row['total_value'],
            row['total_cost'],
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=inventory_report.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


def workbook_response(filename, headers, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Report'
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    for column in sheet.columns:
        width = max(len(str(cell.value or '')) for cell in column) + 2
        sheet.column_dimensions[column[0].column_letter].width = min(width, 42)

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def sales_excel_response(sales):
    rows = [[sale.sale_date.strftime('%Y-%m-%d %H:%M'), sale.product.name, sale.quantity, float(sale.selling_price), float(sale.total_amount)] for sale in sales]
    return workbook_response('sales_report.xlsx', ['Date', 'Product', 'Quantity', 'Selling Price', 'Total'], rows)


def inventory_excel_response(report_rows):
    rows = [[row['name'], row['sku'], row['quantity'], float(row['price']), float(row['cost_price']), float(row['total_value']), float(row['total_cost'])] for row in report_rows]
    return workbook_response('inventory_report.xlsx', ['Product', 'SKU', 'Quantity', 'Price', 'Cost Price', 'Total Value', 'Total Cost'], rows)


def movement_excel_response(summary):
    rows = []
    for item in summary['incoming']:
        rows.append([item.created_at.strftime('%Y-%m-%d %H:%M'), 'Incoming', item.product.name, item.quantity, item.supplier.name if item.supplier else '', item.note or ''])
    for item in summary['outgoing']:
        rows.append([item.sale_date.strftime('%Y-%m-%d %H:%M'), 'Outgoing', item.product.name, item.quantity, item.customer.name if item.customer else 'Walk-in Customer', item.destination_details or ''])
    rows.sort(key=lambda value: value[0], reverse=True)
    return workbook_response('inventory_movement.xlsx', ['Date', 'Type', 'Product', 'Quantity', 'Party', 'Notes'], rows)


def inventory_pdf_response(report_rows, totals=None):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle('Inventory Report')
    pdf.drawString(40, 750, 'Inventory Report')
    y = 720
    if totals:
        pdf.drawString(40, 740, f"Total Inventory Value: {totals.get('value', 0):.2f}")
        y -= 20

    for row in report_rows:
        line = f"{row['name']} | SKU: {row['sku']} | Qty: {row['quantity']} | Value: {row['total_value']:.2f}"
        pdf.drawString(40, y, line[:100])
        y -= 18
        if y < 60:
            pdf.showPage()
            y = 750

    pdf.save()
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=inventory_report.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response


def movement_pdf_response(summary):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle('Inventory Movement Report')
    pdf.drawString(40, 750, 'Inventory Movement Report')
    pdf.drawString(40, 730, f"Incoming: {summary['incoming_qty']}  Outgoing: {summary['outgoing_qty']}  Net: {summary['net_qty']}")
    y = 700
    for row in summary['product_rows']:
        line = f"{row['product'].name} | In: {row['incoming']} | Out: {row['outgoing']} | Net: {row['net']}"
        pdf.drawString(40, y, line[:100])
        y -= 18
        if y < 60:
            pdf.showPage()
            y = 750
    pdf.save()
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=inventory_movement.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response


def profit_csv_response(summary):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Revenue', 'Cost', 'Profit'])
    writer.writerow([summary['revenue'], summary['cost'], summary['profit']])
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=profit_loss.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


def profit_pdf_response(summary):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle('Profit and Loss Summary')
    pdf.drawString(40, 750, 'Profit and Loss Summary')
    pdf.drawString(40, 720, f"Revenue: {summary['revenue']:.2f}")
    pdf.drawString(40, 700, f"Cost: {summary['cost']:.2f}")
    pdf.drawString(40, 680, f"Profit: {summary['profit']:.2f}")
    pdf.save()
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=profit_loss.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response


def invoice_pdf_response(invoice):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle(f'Invoice {invoice.invoice_number}')
    pdf.drawString(40, 750, f'Invoice: {invoice.invoice_number}')
    pdf.drawString(40, 730, f'Date: {invoice.issued_at:%Y-%m-%d %H:%M}')
    pdf.drawString(40, 710, f'Customer: {invoice.customer.name if invoice.customer else "Walk-in Customer"}')

    y = 670
    pdf.drawString(40, y, 'Product')
    pdf.drawString(250, y, 'Qty')
    pdf.drawString(300, y, 'Price')
    pdf.drawString(370, y, 'Tax')
    pdf.drawString(440, y, 'Total')
    y -= 20
    for item in invoice.items:
        pdf.drawString(40, y, item.product.name[:32])
        pdf.drawString(250, y, str(item.quantity))
        pdf.drawString(300, y, f'{item.unit_price:.2f}')
        pdf.drawString(370, y, f'{item.tax_amount:.2f}')
        pdf.drawString(440, y, f'{item.line_total:.2f}')
        y -= 18
        if y < 120:
            pdf.showPage()
            y = 750

    y -= 10
    pdf.drawString(340, y, f'Subtotal: {invoice.subtotal:.2f}')
    y -= 18
    pdf.drawString(340, y, f'Discount: {invoice.discount_amount:.2f}')
    y -= 18
    pdf.drawString(340, y, f'GST/Tax: {invoice.tax_amount:.2f}')
    y -= 18
    pdf.drawString(340, y, f'Total: {invoice.total_amount:.2f}')
    y -= 18
    pdf.drawString(340, y, f'Paid: {invoice.amount_paid:.2f}')
    y -= 18
    pdf.drawString(340, y, f'Balance: {invoice.balance_due:.2f}')
    pdf.save()
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={invoice.invoice_number}.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response
