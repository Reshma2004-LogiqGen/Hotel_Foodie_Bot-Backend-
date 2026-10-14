"""
Food Friend Backend - Kitchen order board (chefs and admins)
An order moves received -> preparing -> ready -> served; served ends the journey.
"""

from datetime import datetime, time

from flask import Blueprint, g, jsonify, request
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from app.auth import staff_required
from app.extensions import db
from app.models import ORDER_STATUSES, Order
from app.timeutil import local_now
from app.utils.validation import ValidationError, get_json_body

kitchen_bp = Blueprint('kitchen', __name__)


@kitchen_bp.route('/kitchen/orders', methods=['GET'])
@staff_required
def list_orders():
    """Every open order, plus the orders served today."""
    start_of_today = datetime.combine(local_now().date(), time.min)
    orders = (
        Order.query.options(selectinload(Order.items))
        .filter(
            Order.restaurant_id == g.restaurant_id,
            or_(Order.status != 'served', Order.updated_at >= start_of_today),
        )
        .order_by(Order.created_at)
        .all()
    )
    return jsonify([order.to_dict() for order in orders])


@kitchen_bp.route('/kitchen/orders/<int:order_id>', methods=['PATCH'])
@staff_required
def update_order_status(order_id):
    order = db.session.get(Order, order_id)
    if order is None or order.restaurant_id != g.restaurant_id:
        return jsonify({'error': 'Order not found.'}), 404

    try:
        status = get_json_body(request).get('status')
        if status not in ORDER_STATUSES:
            raise ValidationError('Choose a valid order status.')
    except ValidationError as e:
        return jsonify({'error': e.message}), 400

    order.status = status
    db.session.commit()
    return jsonify(order.to_dict())
