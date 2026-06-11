from app import db
from app.models.audit_log import log_audit_event
from app.repositories.return_repository import ReturnRepository
from app.services.return_service import approve_return, cancel_return, reject_return, request_return


class ReturnAPIService:
    def __init__(self, repository=None):
        self.repository = repository or ReturnRepository()

    def list_returns(self, *, filters=None, search=None, sort_by=None, sort_order=None, page=1, per_page=20):
        return self.repository.list_returns(
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )

    def get_return(self, return_order_id):
        return self.repository.get_by_id(return_order_id)

    def request_return(self, user, payload, request_context=None):
        if not isinstance(payload, dict):
            raise ValueError('Request payload must be a JSON object.')

        return_type = payload.get('return_type')
        product_id = payload.get('product_id')
        quantity = payload.get('quantity')
        customer_id = payload.get('customer_id')
        supplier_id = payload.get('supplier_id')
        refund_amount = payload.get('refund_amount', 0)
        restock = payload.get('restock', True)
        reason = payload.get('reason')

        if not return_type or product_id is None or quantity is None or reason is None:
            raise ValueError('return_type, product_id, quantity, and reason are required.')

        return_order = request_return(
            return_type=return_type,
            product_id=product_id,
            quantity=quantity,
            user_id=user.get('user_id') or user.get('id'),
            customer_id=customer_id,
            supplier_id=supplier_id,
            refund_amount=refund_amount,
            restock=restock,
            reason=reason,
        )
        db.session.commit()
        log_audit_event(user, request_context, 'RETURN_REQUESTED', f'return_order:{return_order.id}', 'success')
        return return_order

    def approve_return(self, user, return_order_id, request_context=None):
        return_order = approve_return(return_order_id, user.get('user_id') or user.get('id'))
        db.session.commit()
        log_audit_event(user, request_context, 'RETURN_APPROVED', f'return_order:{return_order.id}', 'success')
        return return_order

    def reject_return(self, user, return_order_id, payload, request_context=None):
        if not isinstance(payload, dict):
            raise ValueError('Request payload must be a JSON object.')
        reason = payload.get('reason')
        return_order = reject_return(return_order_id, user.get('user_id') or user.get('id'), reason=reason)
        db.session.commit()
        log_audit_event(user, request_context, 'RETURN_REJECTED', f'return_order:{return_order.id}', 'success')
        return return_order

    def cancel_return(self, user, return_order_id, payload, request_context=None):
        if not isinstance(payload, dict):
            raise ValueError('Request payload must be a JSON object.')

        return_order = self.repository.get_by_id(return_order_id)
        if return_order is None:
            raise ValueError('Return order not found')

        user_id = user.get('user_id') or user.get('id')
        user_role = user.get('role')
        if return_order.created_by != user_id and user_role not in ('admin', 'manager'):
            raise ValueError('You do not have permission to cancel this return.')

        reason = payload.get('reason')
        cancelled = cancel_return(return_order_id, user_id, reason=reason)
        db.session.commit()
        log_audit_event(user, request_context, 'RETURN_CANCELLED', f'return_order:{cancelled.id}', 'success')
        return cancelled


ReturnService = ReturnAPIService
