import json
import re
from datetime import datetime, timezone
from functools import wraps

from flask import jsonify, request
from werkzeug.exceptions import BadRequest, HTTPException, RequestEntityTooLarge


class APIResponse:
    """Standard API response format."""

    @staticmethod
    def success(data=None, message='Success', status_code=200, **kwargs):
        response = {
            'status': 'success',
            'message': message,
            'data': data,
        }
        response.update(kwargs)
        return jsonify(response), status_code

    @staticmethod
    def error(message='Error', status_code=400, error_code=None, errors=None, **kwargs):
        response = {
            'status': 'error',
            'message': message,
            'error_code': error_code,
        }
        if errors is not None:
            response['errors'] = errors
        response.update(kwargs)
        return jsonify(response), status_code

    @staticmethod
    def paginated(items, total, page, per_page, message='Success', **kwargs):
        response = {
            'status': 'success',
            'message': message,
            'data': items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
            },
        }
        response.update(kwargs)
        return jsonify(response), 200


class APIError(Exception):
    def __init__(self, message='API error', status_code=400, error_code=None, errors=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.errors = errors or {}


class ValidationError(APIError):
    def __init__(self, message='Validation failed', errors=None, error_code='VALIDATION_FAILED'):
        super().__init__(message=message, status_code=400, error_code=error_code, errors=errors)


class Field:
    type_name = 'string'

    def __init__(
        self,
        required=False,
        nullable=False,
        default=None,
        choices=None,
        min_length=None,
        max_length=None,
        min_value=None,
        max_value=None,
        pattern=None,
        description=None,
        example=None,
    ):
        self.required = required
        self.nullable = nullable
        self.default = default
        self.choices = choices
        self.min_length = min_length
        self.max_length = max_length
        self.min_value = min_value
        self.max_value = max_value
        self.pattern = re.compile(pattern) if pattern else None
        self.description = description
        self.example = example

    def deserialize(self, value):
        if value is None:
            if self.required and not self.nullable:
                raise ValidationError('Field is required.', errors={'value': 'Missing required field'})
            return None

        self.validate(value)
        return value

    def validate(self, value):
        if not self.nullable and value is None:
            raise ValidationError('Null value is not allowed.')
        if self.choices is not None and value not in self.choices:
            raise ValidationError(f'Value must be one of {self.choices}.')

    def to_openapi(self):
        schema = {'type': self.type_name}
        if self.description:
            schema['description'] = self.description
        if self.example is not None:
            schema['example'] = self.example
        if self.choices is not None:
            schema['enum'] = list(self.choices)
        if self.min_length is not None:
            schema['minLength'] = self.min_length
        if self.max_length is not None:
            schema['maxLength'] = self.max_length
        if self.min_value is not None:
            schema['minimum'] = self.min_value
        if self.max_value is not None:
            schema['maximum'] = self.max_value
        if self.pattern is not None:
            schema['pattern'] = self.pattern.pattern
        return schema


class String(Field):
    type_name = 'string'

    def validate(self, value):
        super().validate(value)
        if value is None:
            return
        if not isinstance(value, str):
            raise ValidationError('Must be a string.')
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(f'Must be at least {self.min_length} characters long.')
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(f'Must be no more than {self.max_length} characters long.')


class Integer(Field):
    type_name = 'integer'

    def validate(self, value):
        super().validate(value)
        if value is None:
            return
        if not isinstance(value, int):
            raise ValidationError('Must be an integer.')
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(f'Must be greater than or equal to {self.min_value}.')
        if self.max_value is not None and value > self.max_value:
            raise ValidationError(f'Must be less than or equal to {self.max_value}.')


class Float(Field):
    type_name = 'number'

    def validate(self, value):
        super().validate(value)
        if value is None:
            return
        if not isinstance(value, (float, int)):
            raise ValidationError('Must be a number.')
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(f'Must be greater than or equal to {self.min_value}.')
        if self.max_value is not None and value > self.max_value:
            raise ValidationError(f'Must be less than or equal to {self.max_value}.')


class Boolean(Field):
    type_name = 'boolean'

    def validate(self, value):
        super().validate(value)
        if value is None:
            return
        if not isinstance(value, bool):
            raise ValidationError('Must be a boolean.')


class Email(String):
    def validate(self, value):
        super().validate(value)
        if value is None:
            return
        if '@' not in value or '.' not in value:
            raise ValidationError('Must be a valid email address.')


class DateTime(String):
    type_name = 'string'

    def __init__(self, required=False, nullable=False, description=None, example=None):
        super().__init__(required=required, nullable=nullable, description=description, example=example)

    def validate(self, value):
        super().validate(value)
        if value is None:
            return
        if isinstance(value, datetime):
            return
        try:
            datetime.fromisoformat(value)
        except Exception:
            raise ValidationError('Must be a valid ISO 8601 datetime string.')


class Nested(Field):
    type_name = 'object'

    def __init__(self, schema, required=False, nullable=False, description=None, example=None):
        super().__init__(required=required, nullable=nullable, description=description, example=example)
        self.schema = schema

    def validate(self, value):
        super().validate(value)
        if value is None:
            return
        if not isinstance(value, dict):
            raise ValidationError('Must be an object.')
        self.schema().load(value)

    def to_openapi(self):
        return {'$ref': f"#/components/schemas/{self.schema.__name__}"}


class List(Field):
    type_name = 'array'

    def __init__(self, field, required=False, nullable=False, min_length=None, max_length=None, description=None, example=None):
        super().__init__(required=required, nullable=nullable, description=description, example=example)
        self.field = field
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value):
        super().validate(value)
        if value is None:
            return
        if not isinstance(value, list):
            raise ValidationError('Must be a list.')
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(f'Must contain at least {self.min_length} items.')
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(f'Must contain no more than {self.max_length} items.')
        for item in value:
            self.field.deserialize(item)

    def to_openapi(self):
        item_schema = self.field.to_openapi()
        return {
            'type': 'array',
            'items': item_schema,
            **({} if self.description is None else {'description': self.description}),
        }


class SchemaMeta(type):
    def __new__(cls, name, bases, attrs):
        fields = {}
        for key, value in list(attrs.items()):
            if isinstance(value, Field):
                fields[key] = value
                attrs.pop(key)
        attrs['_fields'] = fields
        return super().__new__(cls, name, bases, attrs)


class Schema(metaclass=SchemaMeta):
    def load(self, data, partial=False):
        if data is None:
            raise ValidationError('Request payload is required.', errors={'body': 'Missing JSON body'})
        if not isinstance(data, dict):
            raise ValidationError('Payload must be a JSON object.', errors={'body': 'Invalid JSON object'})

        result = {}
        errors = {}

        for field_name, field in self._fields.items():
            value = data.get(field_name, field.default)
            if value is None and field.required and not partial:
                errors[field_name] = 'This field is required.'
                continue
            try:
                result[field_name] = field.deserialize(value)
            except ValidationError as exc:
                errors[field_name] = exc.message

        if errors:
            raise ValidationError('One or more fields failed validation.', errors=errors)

        return result

    def dump(self, obj):
        result = {}
        for field_name, field in self._fields.items():
            if isinstance(obj, dict):
                value = obj.get(field_name)
            else:
                value = getattr(obj, field_name, None)
            result[field_name] = value
        return result

    @classmethod
    def to_openapi_schema(cls):
        properties = {}
        required = []
        for field_name, field in cls._fields.items():
            field_schema = field.to_openapi()
            if field_schema is not None:
                properties[field_name] = field_schema
            if field.required:
                required.append(field_name)
        schema = {'type': 'object', 'properties': properties}
        if required:
            schema['required'] = required
        return schema


def parse_pagination_params():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    return page, per_page


def parse_filter_params():
    filters = request.args.get('filters') or request.args.get('filter')
    if not filters:
        return {}
    try:
        if isinstance(filters, str) and filters.strip().startswith('{'):
            return json.loads(filters)
    except ValueError:
        pass

    parsed = {}
    for pair in filters.split(','):
        if ':' not in pair:
            continue
        key, value = pair.split(':', 1)
        parsed[key.strip()] = value.strip()
    return parsed


def parse_sort_params():
    sort_by = request.args.get('sort_by') or request.args.get('sort') or 'id'
    sort_order = request.args.get('sort_order') or request.args.get('order') or 'asc'
    if sort_order not in ('asc', 'desc'):
        sort_order = 'asc'
    return sort_by, sort_order


def parse_search_params():
    query = request.args.get('q') or request.args.get('search')
    if not query:
        return ''
    return query.strip()


def require_json():
    if not request.is_json:
        raise ValidationError(
            'Content type must be application/json.',
            errors={'content_type': 'application/json required'},
            error_code='INVALID_CONTENT_TYPE',
        )
    try:
        payload = request.get_json()
    except BadRequest:
        raise ValidationError(
            'Malformed JSON payload.',
            errors={'body': 'Invalid JSON'},
            error_code='INVALID_JSON',
        )
    if payload is None:
        raise ValidationError(
            'Request body is required.',
            errors={'body': 'Empty JSON body'},
            error_code='INVALID_JSON',
        )
    return payload


def register_api_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        if not request.path.startswith('/api/'):
            return error
        return APIResponse.error(
            message=error.message,
            status_code=error.status_code,
            error_code=error.error_code,
            errors=error.errors,
        )

    @app.errorhandler(BadRequest)
    def handle_bad_request(error):
        if not request.path.startswith('/api/'):
            return error
        return APIResponse.error(
            message='Invalid JSON payload or malformed request.',
            status_code=400,
            error_code='INVALID_JSON',
        )

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_too_large(error):
        if not request.path.startswith('/api/'):
            return error
        return APIResponse.error(
            message='Request body too large.',
            status_code=413,
            error_code='REQUEST_ENTITY_TOO_LARGE',
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        if not request.path.startswith('/api/'):
            return error
        return APIResponse.error(
            message=error.description or 'API error.',
            status_code=error.code or 500,
            error_code=error.name.replace(' ', '_').upper() if error.name else 'HTTP_ERROR',
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        if not request.path.startswith('/api/'):
            raise error
        return APIResponse.error(
            message='Unexpected server error.',
            status_code=500,
            error_code='INTERNAL_SERVER_ERROR',
        )


def api_schema_error_response(errors):
    return APIResponse.error(
        message='Validation failed.',
        status_code=400,
        error_code='VALIDATION_FAILED',
        errors=errors,
    )
