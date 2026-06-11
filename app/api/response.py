from flask import jsonify


def json_success(data=None, meta=None, message=None, status_code=200):
    response = {
        'success': True,
        'data': data,
    }
    if message is not None:
        response['message'] = message
    if meta is not None:
        response['meta'] = meta
    return jsonify(response), status_code


def json_error(message='An error occurred', error_code=None, errors=None, status_code=400):
    error_payload = {'message': message}
    if error_code is not None:
        error_payload['code'] = error_code
    if errors is not None:
        error_payload['details'] = errors

    response = {
        'success': False,
        'error': error_payload,
    }
    return jsonify(response), status_code


def json_paginated(data, total, page, per_page, message=None, status_code=200):
    meta = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
    }
    return json_success(data=data, meta=meta, message=message, status_code=status_code)
