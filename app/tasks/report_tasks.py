"""Report generation background tasks."""

from app.tasks.runner import register_task


@register_task('generate_inventory_report', max_retries=2, timeout=300)
def generate_inventory_report_task(format: str = 'pdf', filters: dict = None):
    """Generate inventory report in background."""
    from app.services.report_service import ReportService

    service = ReportService()
    report = service.generate_inventory_report(format=format, filters=filters or {})
    return {
        'report_id': report.id,
        'format': format,
        'file_path': report.file_path,
        'status': 'completed',
    }


@register_task('generate_sales_report', max_retries=2, timeout=300)
def generate_sales_report_task(format: str = 'pdf', filters: dict = None):
    """Generate sales report in background."""
    from app.services.report_service import ReportService

    service = ReportService()
    report = service.generate_sales_report(format=format, filters=filters or {})
    return {
        'report_id': report.id,
        'format': format,
        'file_path': report.file_path,
        'status': 'completed',
    }


@register_task('generate_purchase_report', max_retries=2, timeout=300)
def generate_purchase_report_task(format: str = 'pdf', filters: dict = None):
    """Generate purchase report in background."""
    from app.services.report_service import ReportService

    service = ReportService()
    report = service.generate_purchase_report(format=format, filters=filters or {})
    return {
        'report_id': report.id,
        'format': format,
        'file_path': report.file_path,
        'status': 'completed',
    }


@register_task('export_data', max_retries=2, timeout=600)
def export_data_task(data_type: str, format: str = 'csv'):
    """Export data in background."""
    from app.services.export_service import ExportService

    service = ExportService()
    export = service.export_data(data_type=data_type, format=format)
    return {
        'export_id': export.id,
        'data_type': data_type,
        'format': format,
        'file_path': export.file_path,
        'status': 'completed',
    }
