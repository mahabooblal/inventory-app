from flask import Blueprint, Response, current_app, request, abort
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

bp = Blueprint('metrics', __name__)

@bp.route('/metrics')
def metrics():
    token = current_app.config.get('METRICS_AUTH_TOKEN')
    if token:
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            abort(401)
        supplied = auth.split(' ', 1)[1]
        if supplied != token:
            abort(403)
    data = generate_latest()
    return Response(data, mimetype=CONTENT_TYPE_LATEST)
