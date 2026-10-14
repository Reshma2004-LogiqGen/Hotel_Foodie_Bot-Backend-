"""
Food Friend Backend - "Chat while you wait" persona bot for customers with an order
"""

import threading
import time
from collections import defaultdict, deque

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload

from app.models import Category, MenuItem
from app.prompts.personas import GREETING_REQUEST, LOVER_ROLES, LOVER_STAGES, PERSONAS, build_instructions
from app.routes.public import find_table_order
from app.services import ai_service
from app.services.ai_service import AIUnavailableError
from app.utils.validation import ValidationError, clean_text, get_json_body

chat_bp = Blueprint('chat', __name__)

MAX_MESSAGE_LENGTH = 500
MAX_HISTORY_MESSAGES = 12
MAX_MENU_ITEMS = 120

# Keeps one order from running up the OpenAI bill.
MAX_MESSAGES_PER_ORDER = 60
MESSAGE_WINDOW_SECONDS = 60 * 60
_recent_messages = defaultdict(deque)
_recent_messages_lock = threading.Lock()


def _allow_message(order_id):
    now = time.monotonic()
    with _recent_messages_lock:
        sent = _recent_messages[order_id]
        while sent and now - sent[0] > MESSAGE_WINDOW_SECONDS:
            sent.popleft()
        if len(sent) >= MAX_MESSAGES_PER_ORDER:
            return False
        sent.append(now)
        return True


def _menu_for(restaurant_id):
    """The dishes guests can see, so the buddies only ever talk about real food."""
    return (
        MenuItem.query.options(joinedload(MenuItem.category))
        .join(Category, MenuItem.category_id == Category.id)
        .filter(
            MenuItem.restaurant_id == restaurant_id,
            MenuItem.is_archived.is_(False),
            Category.is_visible.is_(True),
        )
        .order_by(Category.sort_order, Category.id, MenuItem.sort_order, MenuItem.id)
        .limit(MAX_MENU_ITEMS)
        .all()
    )


def _clean_history(raw):
    if not isinstance(raw, list):
        raise ValidationError('Conversation history must be a list.')
    history = []
    for turn in raw[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(turn, dict) or turn.get('role') not in ('user', 'assistant'):
            raise ValidationError('Conversation history is not valid.')
        content = clean_text(turn.get('content'), 'Message', MAX_MESSAGE_LENGTH * 2)
        if content:
            history.append({'role': turn['role'], 'content': content})
    return history


def _clean_lover_config(raw):
    if raw is None:
        return None
    if not isinstance(raw, dict) or raw.get('gender') not in LOVER_ROLES or raw.get('relationshipStatus') not in LOVER_STAGES:
        raise ValidationError('Pick who I should be and your relationship status.')
    return raw


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    Body: {code, orderNumber, persona, message, conversationHistory, loverConfig?}
    An empty message starts the conversation with a greeting.
    """
    try:
        data = get_json_body(request)
        persona = data.get('persona')
        if persona not in PERSONAS:
            raise ValidationError('Pick someone to chat with.')
        message = clean_text(data.get('message'), 'Message', MAX_MESSAGE_LENGTH)
        history = _clean_history(data.get('conversationHistory', []))
        if not message and history:
            raise ValidationError('Type a message.')
        lover_config = _clean_lover_config(data.get('loverConfig')) if persona == 'lover' else None
    except ValidationError as error:
        return jsonify({'error': error.message}), 400

    table, order, error = find_table_order(data.get('code'), data.get('orderNumber'))
    if error:
        return error
    if not _allow_message(order.id):
        return jsonify({'error': "That's a lot of chatting! Take a little break and enjoy your food."}), 429

    instructions = build_instructions(
        persona, lover_config, order.restaurant.name, table.number, order.items, order.status,
        _menu_for(order.restaurant_id),
    )
    messages = history + [{'role': 'user', 'content': message or GREETING_REQUEST}]
    try:
        reply = ai_service.chat_reply(instructions, messages, user_id=f'order-{order.id}')
    except AIUnavailableError as ai_error:
        return jsonify({'error': str(ai_error)}), ai_error.status
    return jsonify({'response': reply})
