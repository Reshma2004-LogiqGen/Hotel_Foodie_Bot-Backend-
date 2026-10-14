"""
Food Friend Backend - Request validation helpers
"""

import re
from decimal import Decimal, InvalidOperation

EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class ValidationError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def get_json_body(request):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError('Request body must be a JSON object.')
    return data


def clean_text(value, field, max_length, required=False):
    if value is None:
        value = ''
    if not isinstance(value, str):
        raise ValidationError(f'{field} must be text.')
    value = value.strip()
    if required and not value:
        raise ValidationError(f'{field} is required.')
    if len(value) > max_length:
        raise ValidationError(f'{field} must be at most {max_length} characters.')
    return value


def clean_int(value, field, minimum, maximum, required=True):
    if value is None or value == '':
        if required:
            raise ValidationError(f'{field} is required.')
        return None
    if isinstance(value, bool):
        raise ValidationError(f'{field} must be a whole number.')
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f'{field} must be a whole number.')
    if isinstance(value, float) and value != number:
        raise ValidationError(f'{field} must be a whole number.')
    if number < minimum or number > maximum:
        raise ValidationError(f'{field} must be between {minimum} and {maximum}.')
    return number


def clean_price(value, field='Price'):
    if value is None or value == '' or isinstance(value, bool):
        raise ValidationError(f'{field} is required.')
    try:
        price = Decimal(str(value)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        raise ValidationError(f'{field} must be a number.')
    if price <= 0 or price > Decimal('100000'):
        raise ValidationError(f'{field} must be between 1 and 100000.')
    return price


def clean_bool(value, field):
    if not isinstance(value, bool):
        raise ValidationError(f'{field} must be true or false.')
    return value


def clean_email(value):
    email = clean_text(value, 'Email', 120, required=True).lower()
    if not EMAIL_PATTERN.match(email):
        raise ValidationError('Enter a valid email address.')
    return email


def clean_new_password(value):
    if not isinstance(value, str) or not value:
        raise ValidationError('Password is required.')
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f'Password must be at least {MIN_PASSWORD_LENGTH} characters.')
    if len(value) > MAX_PASSWORD_LENGTH:
        raise ValidationError(f'Password must be at most {MAX_PASSWORD_LENGTH} characters.')
    return value


def clean_image_url(value):
    value = clean_text(value, 'Image', 500)
    if not value:
        return None
    if not (value.startswith('/uploads/') or value.startswith('https://') or value.startswith('http://')):
        raise ValidationError('Image must be an uploaded file or a web link.')
    return value
