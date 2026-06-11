"""Background task processing module.

Provides:
- Central task registry
- Task execution engine
- Retry and error handling
- Task logging
- Future Celery/RQ compatibility
"""

from app.tasks.runner import TaskRunner, register_task, execute_task, get_task_registry

# Import all task modules to register tasks
from app.tasks import backup_tasks, inventory_tasks, report_tasks, notification_tasks, reconciliation_tasks, maintenance_tasks  # noqa

__all__ = [
    'TaskRunner',
    'register_task',
    'execute_task',
    'get_task_registry',
]
