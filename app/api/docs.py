from flask import Blueprint, render_template, url_for
from app.api.openapi import get_openapi_spec

bp = Blueprint('api_docs', __name__, url_prefix='/api')


@bp.route('/docs', methods=['GET'])
def swagger_ui():
    return render_template('api_docs.html', spec_url=url_for('api_docs.openapi_json'))


@bp.route('/redoc', methods=['GET'])
def redoc_ui():
    return render_template('api_redoc.html', spec_url=url_for('api_docs.openapi_json'))


@bp.route('/openapi.json', methods=['GET'])
def openapi_json():
    return get_openapi_spec()
