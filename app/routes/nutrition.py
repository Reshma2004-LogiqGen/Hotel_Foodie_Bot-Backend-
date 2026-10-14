"""
Food Friend Backend - Nutrition for a customer's order
"""

import threading
from collections import defaultdict

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.routes.public import find_table_order
from app.services.nutrition_service import calculate_order_nutrition

nutrition_bp = Blueprint('nutrition', __name__)

# Work out each order's nutrition once, even if the page asks twice at the same time.
_order_locks = defaultdict(threading.Lock)


@nutrition_bp.route('/orders/<order_number>/nutrition', methods=['GET'])
def order_nutrition(order_number):
    _, order, error = find_table_order(request.args.get('code'), order_number)
    if error:
        return error

    with _order_locks[order.id]:
        db.session.refresh(order)
        if order.nutrition is None:
            order.nutrition = calculate_order_nutrition(order, order.restaurant.name)
            db.session.commit()
    return jsonify(order.nutrition)
