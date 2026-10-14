"""
Food Friend Backend - Per-serving nutrition for common restaurant dishes

Values are for one typical Indian restaurant serving (IFCT 2017 / USDA FoodData Central based).
A dish is matched by the most specific keyword found in its name, then its description;
anything unknown gets a generic value for its type (from its category and veg flag).
"""

import re

# keywords, serving, calories, protein g, carbs g, fat g, fiber g, sugar g, sodium mg, extra highlights
_DISHES = [
    # Rice & biryani
    (('chicken biryani',), '1 plate (~350 g)', 560, 28, 62, 21, 3, 3, 980, ()),
    (('mutton biryani', 'lamb biryani', 'gosht biryani'), '1 plate (~350 g)', 650, 30, 60, 30, 3, 3, 1050, ('Rich in iron',)),
    (('egg biryani',), '1 plate (~350 g)', 520, 20, 64, 20, 3, 3, 900, ()),
    (('prawn biryani', 'fish biryani'), '1 plate (~350 g)', 520, 26, 62, 18, 3, 3, 950, ()),
    (('veg biryani', 'vegetable biryani', 'veg dum biryani'), '1 plate (~350 g)', 450, 10, 70, 14, 5, 5, 850, ()),
    (('paneer biryani',), '1 plate (~350 g)', 560, 20, 64, 24, 4, 4, 900, ('Good calcium',)),
    (('biryani',), '1 plate (~350 g)', 550, 22, 64, 22, 3, 3, 950, ()),
    (('mandi', 'kabsa'), '1 plate (~400 g)', 650, 35, 70, 24, 3, 3, 1000, ()),
    (('pulao', 'pulav', 'pilaf'), '1 plate (~250 g)', 380, 8, 62, 11, 3, 3, 650, ()),
    (('jeera rice',), '1 bowl (~200 g)', 300, 5, 55, 7, 1, 0, 400, ()),
    (('fried rice',), '1 plate (~300 g)', 450, 12, 65, 15, 3, 3, 1100, ()),
    (('curd rice',), '1 bowl (~250 g)', 280, 8, 44, 8, 1, 5, 450, ('Probiotic',)),
    (('khichdi',), '1 bowl (~250 g)', 300, 11, 48, 7, 6, 2, 600, ()),
    (('rice',), '1 bowl (~200 g)', 240, 5, 53, 1, 1, 0, 5, ()),

    # Starters
    (('tandoori chicken',), 'Half (~250 g)', 400, 48, 8, 19, 1, 3, 1100, ()),
    (('chicken tikka masala',), '1 bowl (~250 g)', 450, 32, 14, 30, 2, 7, 1050, ()),
    (('chicken tikka', 'malai tikka', 'reshmi kebab'), '6 pieces (~200 g)', 330, 40, 7, 15, 1, 3, 950, ()),
    (('chicken 65',), '1 plate (~200 g)', 420, 30, 18, 25, 1, 2, 1000, ()),
    (('chilli chicken', 'chili chicken', 'dragon chicken'), '1 plate (~220 g)', 450, 28, 24, 27, 2, 8, 1300, ()),
    (('lollipop',), '6 pieces (~220 g)', 450, 28, 22, 28, 1, 3, 1000, ()),
    (('seekh kebab', 'kebab', 'kabab'), '4 pieces (~180 g)', 380, 30, 8, 25, 1, 2, 900, ()),
    (('fish fry', 'fish tikka', 'apollo fish', 'fish fingers'), '1 plate (~200 g)', 320, 30, 10, 18, 1, 1, 750, ('Omega-3',)),
    (('prawn fry', 'prawns fry', 'golden prawn', 'prawn 65'), '1 plate (~180 g)', 280, 28, 8, 15, 1, 1, 900, ()),
    (('paneer tikka',), '6 pieces (~200 g)', 360, 20, 10, 26, 2, 4, 700, ('Good calcium',)),
    (('chilli paneer', 'chili paneer', 'paneer 65'), '1 plate (~200 g)', 420, 18, 20, 30, 2, 7, 1100, ('Good calcium',)),
    (('manchurian',), '1 plate (~200 g)', 350, 7, 38, 19, 4, 9, 1100, ()),
    (('samosa',), '2 pieces', 310, 5, 32, 18, 3, 2, 420, ()),
    (('pakora', 'pakoda', 'bajji', 'bhajji', 'bhaji'), '1 plate (~150 g)', 300, 7, 30, 17, 4, 2, 450, ()),
    (('spring roll',), '4 pieces', 300, 6, 34, 15, 2, 4, 600, ()),
    (('french fries', 'fries', 'finger chips'), '1 plate (~150 g)', 365, 4, 48, 17, 4, 0, 250, ()),
    (('momos', 'momo', 'dumpling'), '6 pieces', 300, 14, 40, 9, 2, 2, 700, ()),
    (('bread omelette', 'bread omelet'), '1 plate', 330, 15, 30, 16, 2, 3, 600, ()),
    (('omelette', 'omelet'), '2-egg omelette', 190, 13, 2, 14, 1, 1, 350, ()),

    # Curries
    (('butter chicken', 'murgh makhani'), '1 bowl (~250 g)', 490, 30, 14, 35, 2, 8, 1100, ()),
    (('chicken korma', 'mutton korma', 'korma'), '1 bowl (~250 g)', 420, 25, 15, 29, 2, 6, 850, ()),
    (('chicken curry', 'chicken masala', 'kadai chicken', 'kadhai chicken', 'chicken chettinad'), '1 bowl (~250 g)', 380, 30, 10, 24, 2, 4, 900, ()),
    (('rogan josh', 'mutton curry', 'mutton masala', 'gosht'), '1 bowl (~250 g)', 450, 32, 9, 32, 2, 3, 950, ('Rich in iron',)),
    (('fish curry', 'fish masala', 'fish moilee'), '1 bowl (~250 g)', 300, 26, 9, 17, 2, 3, 850, ('Omega-3',)),
    (('prawn curry', 'prawn masala', 'prawns curry'), '1 bowl (~250 g)', 300, 24, 10, 18, 2, 3, 900, ()),
    (('egg curry', 'egg masala', 'anda curry'), '1 bowl (2 eggs)', 300, 16, 10, 22, 2, 4, 700, ()),
    (('palak paneer', 'saag paneer'), '1 bowl (~250 g)', 340, 16, 12, 26, 4, 3, 750, ('Rich in iron', 'Good calcium')),
    (('paneer butter masala', 'butter paneer', 'paneer makhani', 'shahi paneer'), '1 bowl (~250 g)', 450, 17, 15, 36, 2, 8, 900, ('Good calcium',)),
    (('kadai paneer', 'kadhai paneer', 'paneer masala', 'matar paneer', 'paneer'), '1 bowl (~250 g)', 390, 17, 13, 30, 3, 5, 850, ('Good calcium',)),
    (('malai kofta', 'kofta'), '1 bowl (~250 g)', 450, 10, 28, 33, 3, 9, 800, ()),
    (('dal makhani',), '1 bowl (~250 g)', 340, 13, 32, 18, 9, 3, 750, ('Plant protein',)),
    (('dal', 'daal', 'dhal'), '1 bowl (~250 g)', 220, 11, 30, 7, 7, 2, 600, ('Plant protein',)),
    (('chana masala', 'chole', 'chickpea', 'chana'), '1 bowl (~250 g)', 300, 12, 40, 11, 10, 6, 750, ('Plant protein',)),
    (('rajma',), '1 bowl (~250 g)', 280, 12, 38, 9, 10, 3, 700, ('Plant protein',)),
    (('sambar', 'sambhar'), '1 bowl (~250 g)', 150, 7, 22, 4, 6, 4, 600, ()),
    (('aloo gobi', 'aloo matar', 'jeera aloo', 'aloo'), '1 bowl (~200 g)', 220, 5, 25, 12, 5, 5, 600, ()),
    (('mix veg', 'mixed veg', 'veg curry', 'vegetable curry', 'veg kurma', 'veg kolhapuri', 'bhindi', 'baingan'), '1 bowl (~250 g)', 220, 6, 20, 13, 6, 7, 650, ()),

    # Breads & South Indian
    (('butter naan',), '1 piece', 320, 9, 50, 9, 2, 3, 520, ()),
    (('garlic naan',), '1 piece', 300, 9, 50, 7, 2, 3, 550, ()),
    (('naan',), '1 piece', 260, 9, 45, 5, 2, 3, 450, ()),
    (('kulcha',), '1 piece', 280, 8, 45, 8, 2, 3, 500, ()),
    (('paratha', 'parotta', 'porotta'), '1 piece', 300, 6, 40, 13, 3, 1, 400, ()),
    (('roti', 'chapati', 'chapathi', 'phulka'), '2 pieces', 240, 8, 40, 6, 6, 0, 300, ()),
    (('puri', 'poori', 'bhatura'), '2 pieces', 290, 5, 34, 15, 2, 1, 300, ()),
    (('masala dosa',), '1 dosa', 380, 8, 55, 14, 4, 3, 700, ()),
    (('dosa', 'uttapam', 'uthappam'), '1 dosa', 220, 5, 34, 7, 2, 1, 400, ()),
    (('idli', 'idly'), '2 pieces', 120, 4, 25, 1, 2, 0, 300, ('Light choice',)),
    (('vada', 'vadai'), '2 pieces', 290, 9, 30, 15, 4, 1, 450, ()),
    (('upma',), '1 plate (~200 g)', 250, 6, 38, 8, 3, 2, 500, ()),
    (('poha',), '1 plate (~200 g)', 270, 5, 45, 8, 2, 3, 450, ()),
    (('pav bhaji',), '1 plate', 450, 11, 60, 19, 7, 8, 1100, ()),

    # Fast food & soups
    (('pizza',), '2 slices', 560, 24, 66, 22, 4, 7, 1250, ()),
    (('burger',), '1 burger', 500, 24, 45, 25, 3, 8, 950, ()),
    (('sandwich',), '1 sandwich', 350, 13, 40, 15, 4, 5, 750, ()),
    (('noodles', 'chowmein', 'chow mein', 'hakka'), '1 plate (~300 g)', 450, 11, 62, 17, 3, 5, 1200, ()),
    (('pasta',), '1 plate (~300 g)', 520, 16, 65, 21, 4, 8, 900, ()),
    (('soup',), '1 bowl (~250 ml)', 120, 5, 14, 5, 2, 4, 800, ('Light choice',)),
    (('salad',), '1 bowl (~150 g)', 120, 3, 12, 7, 4, 6, 250, ('Light choice',)),

    # Desserts
    (('gulab jamun',), '2 pieces', 300, 4, 45, 12, 1, 35, 90, ()),
    (('rasmalai', 'ras malai'), '2 pieces', 250, 8, 30, 11, 0, 25, 100, ('Good calcium',)),
    (('rasgulla', 'rasagulla', 'rosogolla'), '2 pieces', 190, 4, 38, 2, 0, 33, 40, ()),
    (('kheer', 'payasam', 'phirni'), '1 bowl (~150 g)', 280, 7, 40, 10, 1, 30, 100, ()),
    (('halwa', 'halva', 'kesari'), '1 bowl (~120 g)', 350, 5, 45, 17, 2, 32, 60, ()),
    (('jalebi',), '100 g', 380, 2, 60, 15, 1, 45, 30, ()),
    (('modak', 'ladoo', 'laddu', 'barfi', 'burfi', 'mysore pak', 'peda'), '2 pieces', 300, 5, 40, 14, 1, 30, 50, ()),
    (('kulfi',), '1 kulfi', 230, 6, 26, 12, 0, 22, 70, ()),
    (('ice cream', 'sundae', 'gelato'), '2 scoops', 270, 5, 32, 14, 1, 28, 90, ()),
    (('brownie',), '1 piece', 400, 5, 50, 20, 2, 35, 200, ()),
    (('cake', 'pastry', 'cheesecake'), '1 slice', 350, 5, 50, 15, 1, 32, 300, ()),

    # Drinks
    (('mango lassi',), '1 glass (300 ml)', 300, 8, 50, 7, 1, 45, 110, ()),
    (('lassi',), '1 glass (300 ml)', 260, 8, 40, 7, 0, 36, 120, ('Probiotic',)),
    (('buttermilk', 'chaas', 'majjiga', 'mor'), '1 glass (300 ml)', 60, 3, 5, 3, 0, 4, 400, ('Light choice', 'Probiotic')),
    (('milkshake', 'shake', 'smoothie'), '1 glass (350 ml)', 350, 9, 50, 12, 1, 45, 200, ()),
    (('cold coffee', 'iced coffee', 'frappe'), '1 glass (300 ml)', 220, 6, 32, 7, 0, 28, 130, ()),
    (('coffee', 'cappuccino', 'latte'), '1 cup (200 ml)', 90, 3, 10, 4, 0, 9, 50, ()),
    (('masala chai', 'chai', 'tea'), '1 cup (150 ml)', 90, 3, 12, 3, 0, 10, 40, ()),
    (('fresh lime', 'lime soda', 'lemonade', 'nimbu', 'lime juice', 'mojito'), '1 glass (300 ml)', 90, 0, 23, 0, 0, 21, 300, ()),
    (('juice',), '1 glass (250 ml)', 140, 1, 34, 1, 1, 28, 10, ()),
    (('coke', 'cola', 'pepsi', 'sprite', 'soft drink', 'thums up', 'fanta', 'soda'), '1 can (330 ml)', 140, 0, 39, 0, 0, 39, 45, ()),
    (('water',), '1 bottle', 0, 0, 0, 0, 0, 0, 0, ()),
]

# Used when nothing in the name, description or category matches.
_GENERIC = {
    'dessert': ('1 serving', 300, 5, 42, 13, 1, 30, 100),
    'drink': ('1 glass (300 ml)', 150, 2, 30, 2, 0, 26, 60),
    'bread': ('1 piece', 260, 8, 42, 7, 2, 2, 450),
    'rice': ('1 plate (~300 g)', 450, 12, 65, 15, 3, 3, 800),
    'starter_veg': ('1 plate (~180 g)', 300, 8, 30, 17, 3, 3, 600),
    'starter_nonveg': ('1 plate (~200 g)', 350, 28, 12, 21, 1, 2, 900),
    'main_veg': ('1 bowl (~250 g)', 300, 9, 28, 17, 5, 5, 700),
    'main_nonveg': ('1 bowl (~250 g)', 420, 28, 14, 28, 2, 4, 900),
}
_CATEGORY_WORDS = (
    ('dessert', ('dessert', 'sweet', 'ice cream', 'bakery')),
    ('drink', ('drink', 'beverage', 'juice', 'shake', 'mocktail', 'coffee', 'tea')),
    ('bread', ('bread', 'roti', 'naan')),
    ('rice', ('rice', 'biryani', 'pulao')),
    ('starter', ('starter', 'appetizer', 'snack', 'tandoor', 'kebab', 'chinese')),
)

NUTRIENTS = ('calories', 'protein', 'carbs', 'fat', 'fiber', 'sugar', 'sodium')


def _contains(text, keyword):
    return re.search(rf'\b{re.escape(keyword)}(?:e?s)?\b', text) is not None


def _best_match(text):
    best, best_length = None, 0
    for entry in _DISHES:
        for keyword in entry[0]:
            if len(keyword) > best_length and _contains(text, keyword):
                best, best_length = entry, len(keyword)
    return best


def _generic_kind(category_name, is_veg):
    text = (category_name or '').lower()
    kind = 'main'
    for name, words in _CATEGORY_WORDS:
        if any(word in text for word in words):
            kind = name
            break
    if kind in ('starter', 'main'):
        kind = f'{kind}_{"veg" if is_veg else "nonveg"}'
    return kind


def _highlights(values, extras):
    found = list(extras)
    if values['protein'] >= 20:
        found.insert(0, 'High protein')
    elif values['protein'] >= 12 and 'Plant protein' not in found:
        found.insert(0, 'Good protein')
    if values['fiber'] >= 6:
        found.append('Good fibre')
    if values['carbs'] <= 15 and values['calories'] > 0:
        found.append('Low carb')
    if 0 < values['calories'] <= 200 and 'Light choice' not in found:
        found.append('Light choice')
    if values['sugar'] >= 25:
        found.append('Sweet treat')
    return list(dict.fromkeys(found))[:3]


def lookup(name, description='', category_name='', is_veg=True):
    """Per-serving nutrition for one dish: {servingSize, highlights, calories, protein, ...}."""
    entry = _best_match(name.lower()) or _best_match((description or '').lower())
    if entry:
        serving, *numbers, extras = entry[1:]
    else:
        serving, *numbers = _GENERIC[_generic_kind(category_name, is_veg)]
        extras = ()
    values = dict(zip(NUTRIENTS, (float(n) for n in numbers)))
    return {'servingSize': serving, 'highlights': _highlights(values, extras), **values}


def health_tip(totals, percentages):
    """One friendly sentence about the whole meal."""
    if percentages['sodium'] >= 60:
        return 'This meal is on the salty side, so sip some water with it and go easy on extra pickles.'
    if percentages['sugar'] >= 70:
        return 'A proper sweet treat! Balance it with a lighter, less sugary meal later today.'
    if percentages['protein'] >= 50:
        return f'Great protein boost: about {round(totals["protein"])} g, roughly {percentages["protein"]}% of what you need in a day.'
    if percentages['calories'] >= 60:
        return f'A hearty meal with about {percentages["calories"]}% of your daily calories. A short walk afterwards helps digestion.'
    if percentages['fiber'] < 15:
        return 'Add a salad, dal or veggie side next time for more fibre to keep you fuller for longer.'
    return 'A nicely balanced meal. Enjoy every bite!'
