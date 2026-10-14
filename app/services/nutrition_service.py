"""
Food Friend Backend - Nutrition for a placed order

Per-serving values come from OpenAI when it is set up, otherwise from the built-in
nutrition reference. Values staff typed in the admin menu always win.
"""

from app.services import ai_service, nutrition_reference
from app.services.ai_service import AIUnavailableError
from app.services.nutrition_reference import NUTRIENTS

# Reference daily values for an average adult (2,000 kcal diet).
DAILY_VALUES = {
    'calories': 2000,
    'protein': 50,
    'carbs': 275,
    'fat': 78,
    'fiber': 28,
    'sugar': 50,
    'sodium': 2300,
}

STAFF_VALUES = {'calories': 'calories', 'protein': 'protein_g', 'carbs': 'carbs_g', 'fat': 'fat_g'}

DISH_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['name', 'servingSize', *NUTRIENTS, 'highlights'],
    'properties': {
        'name': {'type': 'string'},
        'servingSize': {'type': 'string', 'description': 'One restaurant serving, e.g. "1 plate (~350 g)"'},
        'calories': {'type': 'number', 'description': 'kcal'},
        'protein': {'type': 'number', 'description': 'grams'},
        'carbs': {'type': 'number', 'description': 'grams'},
        'fat': {'type': 'number', 'description': 'grams'},
        'fiber': {'type': 'number', 'description': 'grams'},
        'sugar': {'type': 'number', 'description': 'grams'},
        'sodium': {'type': 'number', 'description': 'milligrams'},
        'highlights': {
            'type': 'array',
            'items': {'type': 'string'},
            'description': 'Up to 3 short nutrition highlights, e.g. "High protein", "Rich in iron"',
        },
    },
}

NUTRITION_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['dishes', 'healthTip'],
    'properties': {
        'dishes': {'type': 'array', 'items': DISH_SCHEMA},
        'healthTip': {'type': 'string'},
    },
}

INSTRUCTIONS = """You are a registered dietitian who knows restaurant food, especially Indian cuisine.
Estimate the nutrition of ONE standard restaurant serving of each dish you are given.

Rules:
- Base estimates on typical restaurant recipes and portion sizes (restaurant food uses more oil, butter and cream than home cooking), using standard food composition data (IFCT 2017, USDA FoodData Central).
- Use the description, veg/non-veg flag and the guest's cooking notes (e.g. "less oil", "extra cheese") to adjust.
- If the restaurant gives known values for a dish, use exactly those numbers.
- Return the dishes in the same order and with the same names you were given, one entry per dish.
- Realistic values only: calories should roughly equal 4 x protein + 4 x carbs + 9 x fat.
- healthTip: one friendly, specific sentence (max 25 words) about this meal as a whole, e.g. what it is rich in or a simple balance idea. No medical advice."""


def _describe(item):
    dish = item.menu_item
    lines = [f'- {item.name}']
    if dish is not None:
        lines.append(f'  {"Vegetarian" if dish.is_veg else "Non-vegetarian"}')
        if dish.description:
            lines.append(f'  Description: {dish.description}')
        known = {key: getattr(dish, column) for key, column in STAFF_VALUES.items() if getattr(dish, column) is not None}
        if known:
            lines.append('  Known values per serving: ' + ', '.join(f'{k} {v}' for k, v in known.items()))
    if item.notes:
        lines.append(f'  Guest note: {item.notes}')
    return '\n'.join(lines)


def _ai_estimates(order, restaurant_name):
    """(per-dish estimates, health tip) from OpenAI, or None if it isn't available."""
    if not ai_service.is_configured():
        return None
    prompt = f'Restaurant: {restaurant_name}\nDishes:\n' + '\n'.join(_describe(item) for item in order.items)
    try:
        result = ai_service.structured(
            INSTRUCTIONS, prompt, 'order_nutrition', NUTRITION_SCHEMA, user_id=f'order-{order.id}',
        )
    except AIUnavailableError:
        return None
    if len(result['dishes']) != len(order.items):
        return None
    estimates = [
        {
            'servingSize': dish['servingSize'],
            'highlights': dish['highlights'][:3],
            **{key: max(0.0, float(dish[key])) for key in NUTRIENTS},
        }
        for dish in result['dishes']
    ]
    return estimates, result['healthTip'].strip()


def _reference_estimate(item):
    dish = item.menu_item
    if dish is None:
        return nutrition_reference.lookup(item.name)
    category = dish.category.name if dish.category else ''
    return nutrition_reference.lookup(dish.name, dish.description, category, dish.is_veg)


def _round(key, value):
    return round(value) if key in ('calories', 'sodium') else round(value, 1)


def calculate_order_nutrition(order, restaurant_name):
    """Nutrition for every dish in the order (times its quantity), totals and % of daily values."""
    ai_result = _ai_estimates(order, restaurant_name)
    if ai_result:
        estimates, tip = ai_result
    else:
        estimates, tip = [_reference_estimate(item) for item in order.items], ''

    items = []
    totals = dict.fromkeys(NUTRIENTS, 0.0)
    for item, estimate in zip(order.items, estimates):
        per_serving = {key: estimate[key] for key in NUTRIENTS}
        if item.menu_item is not None:
            for key, column in STAFF_VALUES.items():
                staff_value = getattr(item.menu_item, column)
                if staff_value is not None:
                    per_serving[key] = float(staff_value)

        items.append({
            'name': item.name,
            'quantity': item.quantity,
            'servingSize': estimate['servingSize'],
            'highlights': estimate['highlights'],
            **{key: _round(key, per_serving[key] * item.quantity) for key in NUTRIENTS},
        })
        for key in NUTRIENTS:
            totals[key] += per_serving[key] * item.quantity

    totals = {key: _round(key, value) for key, value in totals.items()}
    percentages = {key: round(totals[key] / DAILY_VALUES[key] * 100) for key in NUTRIENTS}
    return {
        'items': items,
        'totals': totals,
        'dailyPercentages': percentages,
        'healthTip': tip or nutrition_reference.health_tip(totals, percentages),
    }
