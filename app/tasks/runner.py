"""Central task execution engine and registry.

Provides:
- Task registration via decorators
- Task execution with retry logic
- Error handling and logging
- Future Celery/RQ compatibility through abstraction
- Support for both synchronous (testing) and threaded execution
"""

import logging
import functools
import threading
from typing import Dict, Any, Optional, Callable
from flask import current_app

logger = logging.getLogger(__name__)


class TaskRunner:
    """Central task execution engine with registry and retry support."""

    def __init__(self):
        """Initialize the task runner."""
        self.registry: Dict[str, Callable] = {}
        self.logger = logger

    def register(self, task_name: str, max_retries: int = 3, timeout: Optional[int] = None):
        """Decorator to register a task.

        Args:
            task_name: Unique task identifier
            max_retries: Maximum retry attempts
            timeout: Task timeout in seconds (for future async support)
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            # Store metadata for Celery/RQ compatibility
            wrapper._task_name = task_name
            wrapper._max_retries = max_retries
            wrapper._timeout = timeout

            # Register in global registry
            self.registry[task_name] = wrapper
            self.logger.debug(f'Task registered: {task_name} (max_retries={max_retries})')
            return wrapper

        return decorator

    def execute(
        self,
        task_name: str,
        payload: Optional[Dict[str, Any]] = None,
        max_retries: Optional[int] = None,
        attempt: int = 1,
        enqueue: bool = False,
    ) -> Any:
        """Execute a registered task with retry logic.

        Args:
            task_name: Registered task identifier
            payload: Task payload/arguments
            max_retries: Override registered max_retries
            attempt: Current attempt number
            enqueue: If True, run in background thread (unless in testing mode)

        Returns:
            Task result or thread object
        """
        if task_name not in self.registry:
            error_msg = f'Task not registered: {task_name}'
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        task_func = self.registry[task_name]
        payload = payload or {}

        def _execute_internal():
            max_retries_val = max_retries or getattr(task_func, '_max_retries', 3)

            try:
                self.logger.info(
                    f'Executing task: {task_name} (attempt {attempt}/{max_retries_val + 1})'
                )
                result = task_func(**payload)
                self.logger.info(f'Task completed successfully: {task_name}')
                return {
                    'success': True,
                    'result': result,
                    'error': None,
                    'attempt': attempt,
                    'task_name': task_name,
                }
            except Exception as exc:
                error_msg = str(exc)
                self.logger.error(
                    f'Task failed: {task_name} (attempt {attempt}/{max_retries_val + 1}): {error_msg}'
                )

                # If retries remain, signal for retry
                if attempt <= max_retries_val:
                    self.logger.info(f'Task eligible for retry: {task_name}')
                    return {
                        'success': False,
                        'result': None,
                        'error': error_msg,
                        'attempt': attempt,
                        'task_name': task_name,
                        'retry_eligible': True,
                    }

                # All retries exhausted
                return {
                    'success': False,
                    'result': None,
                    'error': error_msg,
                    'attempt': attempt,
                    'task_name': task_name,
                    'retry_eligible': False,
                }

        # In testing mode, run synchronously; otherwise respect enqueue flag
        if current_app and current_app.config.get('TESTING'):
            return _execute_internal()

        if enqueue:
            # Run in background thread
            thread = threading.Thread(target=_execute_internal, daemon=True)
            thread.start()
            return thread

        # Run synchronously
        return _execute_internal()

    def enqueue(self, fn, *args, **kwargs):
        """Legacy enqueue method for backward compatibility.
        
        In testing mode runs synchronously; otherwise runs in thread.
        """
        if current_app and current_app.config.get('TESTING'):
            return fn(*args, **kwargs)

        thread = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread

    def get_task(self, task_name: str) -> Optional[Callable]:
        """Retrieve a registered task by name."""
        return self.registry.get(task_name)

    def list_tasks(self) -> Dict[str, Dict[str, Any]]:
        """List all registered tasks with metadata."""
        return {
            name: {
                'name': name,
                'max_retries': getattr(func, '_max_retries', 3),
                'timeout': getattr(func, '_timeout', None),
            }
            for name, func in self.registry.items()
        }


# Global task runner instance
_task_runner = TaskRunner()


def register_task(task_name: str, max_retries: int = 3, timeout: Optional[int] = None):
    """Register a task using the global runner.

    Usage:
        @register_task('backup_inventory', max_retries=2)
        def backup_inventory_task():
            ...
    """
    return _task_runner.register(task_name, max_retries, timeout)


def execute_task(
    task_name: str,
    payload: Optional[Dict[str, Any]] = None,
    max_retries: Optional[int] = None,
    attempt: int = 1,
    enqueue: bool = False,
) -> Any:
    """Execute a registered task via the global runner.
    
    Args:
        task_name: Registered task identifier
        payload: Task payload/arguments
        max_retries: Override registered max_retries
        attempt: Current attempt number
        enqueue: If True, run in background thread
    """
    return _task_runner.execute(task_name, payload, max_retries, attempt, enqueue)


def get_task_registry() -> TaskRunner:
    """Get the global task runner instance."""
    return _task_runner


# Backward compatibility
task_runner = _task_runner
