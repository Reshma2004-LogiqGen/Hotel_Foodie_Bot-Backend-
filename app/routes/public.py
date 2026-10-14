"""
Food Friend Backend - Public routes used by the customer app
A customer always arrives from a table QR code (/t/<number>?code=<code>);
the code tells us which restaurant and table they are at.
"""

import hmac
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from decimal import Decimal

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import (
    JOIN_CODE_ALPHABET, TABLE_PIN_LENGTH, Category, DiningTable, MenuItem, Order, OrderItem, TableScan,
)
from app.utils.validation import ValidationError, clean_int, clean_text, get_json_body

public_bp = Blueprint('public', __name__)

SCAN_AGAIN = 'Please scan the QR code on your table again.'
MAX_ORDER_LINES = 30
MAX_QUANTITY = 20
ORDER_NUMBER_LENGTH = 6

# Wrong PINs are limited per table number, so nobody can try all 10,000 PINs for a table.
MAX_WRONG_PINS = 8
WRONG_PIN_WINDOW_SECONDS = 10 * 60
_wrong_pins = defaultdict(deque)
_wrong_pins_lock = threading.Lock()

# One table has at most one unserved order; this stops two phones placing orders at the same moment.
_place_order_lock = threading.Lock()


def _table_from_code(code, number=None):
    """Find the active table a QR code belongs to, or return (None, error response)."""
    if not code:
        return None, (jsonify({'error': SCAN_AGAIN}), 400)
    table = DiningTable.query.filter_by(code=code).first()
    if table is None or not hmac.compare_digest(code.encode(), table.code.encode()) or (
        number is not None and table.number != number
    ):
        return None, (jsonify({'error': 'This QR code is no longer valid. Please ask the staff.'}), 403)
    if not table.is_active:
        return None, (jsonify({'error': 'This table is not available. Please ask the staff.'}), 404)
    return table, None


def _active_order(table):
    """The table's latest order that has not been served yet, or None."""
    return (
        Order.query.options(selectinload(Order.items))
        .filter(
            Order.restaurant_id == table.restaurant_id,
            Order.table_number == table.number,
            Order.status != 'served',
        )
        .order_by(Order.created_at.desc(), Order.id.desc())
        .first()
    )


def _new_order_number():
    while True:
        number = ''.join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(ORDER_NUMBER_LENGTH))
        if Order.query.filter_by(order_number=number).first() is None:
            return number


@public_bp.route('/menu', methods=['GET'])
def get_menu():
    table, error = _table_from_code(request.args.get('code'))
    if error:
        return error

    categories = (
        Category.query.filter(Category.restaurant_id == table.restaurant_id, Category.is_visible.is_(True))
        .order_by(Category.sort_order, Category.id)
        .all()
    )
    items = (
        MenuItem.query.filter(
            MenuItem.is_archived.is_(False),
            MenuItem.category_id.in_([c.id for c in categories]),
        )
        .order_by(MenuItem.sort_order, MenuItem.id)
        .all()
    )

    items_by_category = {}
    for item in items:
        items_by_category.setdefault(item.category_id, []).append(item.to_dict())

    return jsonify({
        'restaurant': table.restaurant.to_dict(),
        'categories': [
            {**c.to_dict(), 'items': items_by_category.get(c.id, [])}
            for c in categories
            if items_by_category.get(c.id)
        ],
    })


@public_bp.route('/tables/<int:number>', methods=['GET'])
def check_table(number):
    """Confirm the scanned QR code is valid, record the scan and return the table's order in progress."""
    table, error = _table_from_code(request.args.get('code'), number)
    if error:
        return error

    db.session.add(TableScan(table_id=table.id))
    db.session.commit()
    active = _active_order(table)
    return jsonify({
        'number': table.number,
        'restaurant': table.restaurant.to_dict(),
        'activeOrder': active.to_dict() if active else None,
    })


def _recent_wrong_pins(number, now):
    attempts = _wrong_pins[number]
    while attempts and now - attempts[0] > WRONG_PIN_WINDOW_SECONDS:
        attempts.popleft()
    return attempts


@public_bp.route('/tables/find', methods=['POST'])
def find_table():
    """For customers who can't scan: table number + the PIN printed on the table card."""
    try:
        data = get_json_body(request)
        number = clean_int(data.get('number'), 'Table number', 1, 100000)
        pin = data.get('pin')
        if not isinstance(pin, str) or not re.fullmatch(rf'\d{{{TABLE_PIN_LENGTH}}}', pin.strip()):
            raise ValidationError(f'Enter the {TABLE_PIN_LENGTH}-digit PIN printed on your table card.')
        pin = pin.strip()
    except ValidationError as e:
        return jsonify({'error': e.message}), 400

    now = time.monotonic()
    with _wrong_pins_lock:
        if len(_recent_wrong_pins(number, now)) >= MAX_WRONG_PINS:
            return jsonify({'error': 'Too many wrong tries. Please scan the QR code or ask the staff.'}), 429

    table = DiningTable.query.filter_by(number=number, pin=pin).first()
    if table is None:
        with _wrong_pins_lock:
            _recent_wrong_pins(number, now).append(now)
        return jsonify({'error': 'That table number and PIN do not match. Please check your table card.'}), 404
    if not table.is_active:
        return jsonify({'error': 'This table is not available. Please ask the staff.'}), 404

    return jsonify({'number': table.number, 'code': table.code})


def _clean_order_lines(raw_lines, restaurant_id):
    """Turn [{id, quantity, notes}] into (menu item, quantity, notes) using the restaurant's live menu."""
    if not isinstance(raw_lines, list) or not raw_lines:
        raise ValidationError('Add at least one dish to your order.')
    if len(raw_lines) > MAX_ORDER_LINES:
        raise ValidationError(f'An order can have at most {MAX_ORDER_LINES} different dishes.')

    lines = []
    for raw in raw_lines:
        if not isinstance(raw, dict):
            raise ValidationError('Your order could not be read. Please try again.')
        item_id = clean_int(raw.get('id'), 'Dish', 1, 2**31 - 1)
        quantity = clean_int(raw.get('quantity'), 'Quantity', 1, MAX_QUANTITY)
        notes = clean_text(raw.get('notes'), 'Dish notes', 300)
        lines.append((item_id, quantity, notes))

    menu_items = {
        item.id: item
        for item in MenuItem.query.filter(
            MenuItem.restaurant_id == restaurant_id,
            MenuItem.id.in_([item_id for item_id, _, _ in lines]),
        )
    }
    cleaned = []
    for item_id, quantity, notes in lines:
        item = menu_items.get(item_id)
        if item is None or item.is_archived or (item.category and not item.category.is_visible):
            raise ValidationError('A dish in your cart is no longer on the menu. Please review your cart.')
        if not item.is_available:
            raise ValidationError(f'Sorry, {item.name} just sold out. Please remove it from your cart.')
        cleaned.append((item, quantity, notes))
    return cleaned


@public_bp.route('/orders', methods=['POST'])
def place_order():
    """A customer places an order from their table. Prices always come from the menu, never the client."""
    try:
        data = get_json_body(request)
        table_number = clean_int(data.get('tableNumber'), 'Table number', 1, 100000)
        table, error = _table_from_code(data.get('code'), table_number)
        if error:
            return error
        lines = _clean_order_lines(data.get('items'), table.restaurant_id)
        notes = clean_text(data.get('notes'), 'Cooking instructions', 500)
    except ValidationError as e:
        return jsonify({'error': e.message}), 400

    with _place_order_lock:
        active = _active_order(table)
        if active is not None:
            return jsonify({
                'error': 'This table already has an order in progress.',
                'activeOrder': active.to_dict(),
            }), 409

        order = Order(
            restaurant_id=table.restaurant_id,
            order_number=_new_order_number(),
            table_number=table.number,
            notes=notes,
            total=sum((item.price * quantity for item, quantity, _ in lines), Decimal('0')),
        )
        for item, quantity, item_notes in lines:
            order.items.append(OrderItem(
                menu_item_id=item.id, name=item.name, unit_price=item.price, quantity=quantity, notes=item_notes,
            ))
        db.session.add(order)
        db.session.commit()
    return jsonify(order.to_dict()), 201


def find_table_order(code, order_number):
    """The order, only for the table that placed it. Returns (table, order, error response)."""
    table, error = _table_from_code(code)
    if error:
        return None, None, error
    order = (
        Order.query.options(selectinload(Order.items))
        .filter_by(
            order_number=str(order_number or '').upper(),
            restaurant_id=table.restaurant_id,
            table_number=table.number,
        )
        .first()
    )
    if order is None:
        return table, None, (jsonify({'error': 'We could not find this order. Please ask the staff.'}), 404)
    return table, order, None


@public_bp.route('/orders/<order_number>', methods=['GET'])
def track_order(order_number):
    """Live status of an order, for the table that placed it."""
    _, order, error = find_table_order(request.args.get('code'), order_number)
    if error:
        return error
    return jsonify(order.to_dict())
