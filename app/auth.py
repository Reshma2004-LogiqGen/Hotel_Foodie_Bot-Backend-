"""
Food Friend Backend - Staff authentication helpers
"""

from functools import wraps

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.extensions import db
from app.models import ROLE_ADMIN, STAFF_ROLES, AdminUser

TOKEN_SALT = 'admin-auth'
TOKEN_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=TOKEN_SALT)


def create_admin_token(user):
    return _serializer().dumps({'admin_id': user.id})


def _user_from_token(token):
    try:
        data = _serializer().loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    user = db.session.get(AdminUser, data.get('admin_id'))
    return user if user is not None and user.restaurant_id is not None else None


def _login_required(roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            header = request.headers.get('Authorization', '')
            scheme, _, token = header.partition(' ')
            user = _user_from_token(token) if scheme.lower() == 'bearer' and token else None
            if user is None:
                return jsonify({'error': 'Please log in again.'}), 401
            if user.role not in roles:
                return jsonify({'error': "You don't have access to this page."}), 403
            g.admin = user
            g.restaurant_id = user.restaurant_id
            return view(*args, **kwargs)

        return wrapped

    return decorator


admin_required = _login_required((ROLE_ADMIN,))
staff_required = _login_required(STAFF_ROLES)
