"""
Food Friend Backend - Staff registration and login routes (admin and chef)
An admin registers by creating a restaurant. Chefs join an existing restaurant
with its restaurant code; an admin can later promote a chef to admin.
"""

import threading
import time
from collections import defaultdict, deque

from flask import Blueprint, g, jsonify, request

from app.auth import create_admin_token, staff_required
from app.extensions import db
from app.models import JOIN_CODE_LENGTH, ROLE_ADMIN, STAFF_ROLES, AdminUser, Restaurant, generate_join_code
from app.timeutil import local_now
from app.utils.validation import (
    ValidationError,
    clean_email,
    clean_new_password,
    clean_text,
    get_json_body,
)

admin_auth_bp = Blueprint('admin_auth', __name__)

# Wrong passwords are limited per email, so nobody can keep guessing a staff password.
MAX_WRONG_LOGINS = 10
WRONG_LOGIN_WINDOW_SECONDS = 15 * 60
_wrong_logins = defaultdict(deque)
_wrong_logins_lock = threading.Lock()


def _recent_wrong_logins(email, now):
    attempts = _wrong_logins[email]
    while attempts and now - attempts[0] > WRONG_LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    return attempts


def _find_restaurant_by_code(value):
    code = clean_text(value, 'Restaurant code', 20, required=True).upper().replace(' ', '')
    restaurant = Restaurant.query.filter_by(join_code=code).first() if len(code) == JOIN_CODE_LENGTH else None
    if restaurant is None:
        raise ValidationError('No restaurant has this code. Ask your restaurant admin for the code.')
    return restaurant


@admin_auth_bp.route('/auth/register', methods=['POST'])
def register():
    try:
        data = get_json_body(request)
        name = clean_text(data.get('name'), 'Name', 80, required=True)
        email = clean_email(data.get('email'))
        password = clean_new_password(data.get('password'))
        role = data.get('role')
        if role not in STAFF_ROLES:
            raise ValidationError('Choose Restaurant admin or Chef.')

        restaurant = None
        if role == ROLE_ADMIN:
            restaurant_name = clean_text(data.get('restaurantName'), 'Restaurant name', 100, required=True)
        else:
            restaurant = _find_restaurant_by_code(data.get('restaurantCode'))
    except ValidationError as e:
        return jsonify({'error': e.message}), 400

    if AdminUser.query.filter_by(email=email).first() is not None:
        return jsonify({'error': 'An account with this email already exists.'}), 409

    if restaurant is None:
        restaurant = Restaurant(name=restaurant_name, join_code=generate_join_code())
        db.session.add(restaurant)

    user = AdminUser(name=name, email=email, role=role, restaurant=restaurant, last_login_at=local_now())
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'token': create_admin_token(user), 'user': user.to_dict()}), 201


@admin_auth_bp.route('/auth/login', methods=['POST'])
def login():
    try:
        data = get_json_body(request)
        email = clean_text(data.get('email'), 'Email', 120, required=True).lower()
        password = data.get('password')
        if not isinstance(password, str) or not password:
            raise ValidationError('Password is required.')
    except ValidationError as e:
        return jsonify({'error': e.message}), 400

    now = time.monotonic()
    with _wrong_logins_lock:
        if len(_recent_wrong_logins(email, now)) >= MAX_WRONG_LOGINS:
            return jsonify({'error': 'Too many wrong tries. Please wait 15 minutes and try again.'}), 429

    user = AdminUser.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        with _wrong_logins_lock:
            _recent_wrong_logins(email, now).append(now)
        return jsonify({'error': 'Invalid email or password.'}), 401

    with _wrong_logins_lock:
        _wrong_logins.pop(email, None)
    user.last_login_at = local_now()
    db.session.commit()
    return jsonify({'token': create_admin_token(user), 'user': user.to_dict()})


@admin_auth_bp.route('/auth/me', methods=['GET'])
@staff_required
def me():
    return jsonify({'user': g.admin.to_dict()})
