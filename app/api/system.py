from flask import Blueprint
from app.api.base import APIResponse
from app import limiter

bp = Blueprint('api_system', __name__, url_prefix='/api/v1')


@bp.route('/ping', methods=['GET'])
@limiter.limit('10 per minute')
def ping():
    return APIResponse.success(
        data={'api_version': 'v1', 'message': 'pong'},
        message='API connectivity check successful',
    )
