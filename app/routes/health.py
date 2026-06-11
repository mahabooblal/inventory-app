from flask import Blueprint, jsonify

from app import db

bp = Blueprint('health', __name__)


@bp.route('/health')
def health_check():
    status = {'status': 'ok', 'db': 'unknown'}
    try:
        db.session.execute(db.text('SELECT 1'))
        status['db'] = 'connected'
    except Exception as error:
        status['status'] = 'degraded'
        status['db'] = 'error'
        status['error'] = str(error)
    return jsonify(status), 200 if status['status'] == 'ok' else 503
