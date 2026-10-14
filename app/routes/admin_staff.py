"""
Food Friend Backend - Restaurant settings and team members
"""

from flask import Blueprint, g, jsonify, request

from app.auth import admin_required
from app.extensions import db
from app.models import STAFF_ROLES, AdminUser, Restaurant, generate_join_code
from app.utils.validation import ValidationError, clean_text, get_json_body

admin_staff_bp = Blueprint('admin_staff', __name__)


def _error(message, status=400):
    return jsonify({'error': message}), status


def _restaurant():
    return db.session.get(Restaurant, g.restaurant_id)


def _get_member_or_error(user_id):
    user = db.session.get(AdminUser, user_id)
    if user is None or user.restaurant_id != g.restaurant_id:
        return None, _error('Team member not found.', 404)
    if user.id == g.admin.id:
        return None, _error("You can't change your own account here.")
    return user, None


# ==================== RESTAURANT ====================

@admin_staff_bp.route('/admin/restaurant', methods=['GET'])
@admin_required
def get_restaurant():
    return jsonify(_restaurant().to_dict(include_code=True))


@admin_staff_bp.route('/admin/restaurant', methods=['PATCH'])
@admin_required
def update_restaurant():
    try:
        data = get_json_body(request)
        name = clean_text(data.get('name'), 'Restaurant name', 100, required=True)
    except ValidationError as e:
        return _error(e.message)

    restaurant = _restaurant()
    restaurant.name = name
    db.session.commit()
    return jsonify(restaurant.to_dict(include_code=True))


@admin_staff_bp.route('/admin/restaurant/join-code', methods=['POST'])
@admin_required
def regenerate_join_code():
    restaurant = _restaurant()
    restaurant.join_code = generate_join_code()
    db.session.commit()
    return jsonify(restaurant.to_dict(include_code=True))


# ==================== TEAM ====================

@admin_staff_bp.route('/admin/staff', methods=['GET'])
@admin_required
def list_staff():
    users = (
        AdminUser.query.filter_by(restaurant_id=g.restaurant_id)
        .order_by(AdminUser.role, AdminUser.created_at)
        .all()
    )
    return jsonify([u.to_dict() for u in users])


@admin_staff_bp.route('/admin/staff/<int:user_id>', methods=['PATCH'])
@admin_required
def update_staff(user_id):
    user, error = _get_member_or_error(user_id)
    if error:
        return error

    try:
        role = get_json_body(request).get('role')
        if role not in STAFF_ROLES:
            raise ValidationError('Choose Restaurant admin or Chef.')
    except ValidationError as e:
        return _error(e.message)

    user.role = role
    db.session.commit()
    return jsonify(user.to_dict())


@admin_staff_bp.route('/admin/staff/<int:user_id>', methods=['DELETE'])
@admin_required
def remove_staff(user_id):
    user, error = _get_member_or_error(user_id)
    if error:
        return error

    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})
