"""
Food Friend Backend - Starter data
Gives a restaurant a starter menu and tables 1-10.
    python -m app.seed                  (first restaurant, or a new "Demo Restaurant")
    python -m app.seed --code K7M2QX    (the restaurant with this restaurant code)
Existing data is never overwritten.
"""

import argparse
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import Category, DiningTable, MenuItem, Restaurant, generate_join_code, generate_table_pin

PHOTO = 'https://www.themealdb.com/images/media/meals/{}.jpg'

STARTER_MENU = [
    ('Starters', [
        dict(name='Tandoori Chicken', description='Chicken marinated in yogurt and spices, roasted in the tandoor.',
             price=320, is_veg=False, spice_level=2, prep_minutes=20, photo='qptpvt1487339892'),
        dict(name='Masala Fish Fry', description='Goan-style fish fillet in a tangy red masala, pan-fried.',
             price=340, is_veg=False, spice_level=2, prep_minutes=18, photo='uwxusv1487344500'),
        dict(name='Bread Omelette', description='Fluffy masala omelette folded with toasted bread.',
             price=90, is_veg=False, spice_level=1, prep_minutes=8, photo='hqaejl1695738653'),
    ]),
    ('Biryani & Rice', [
        dict(name='Mutton Biryani', description='Slow-cooked basmati rice layered with tender spiced mutton.',
             price=380, is_veg=False, spice_level=2, prep_minutes=25, photo='xrttsx1487339558'),
        dict(name='Chicken Mandi', description='Smoky Arabian-style rice with juicy roasted chicken.',
             price=360, is_veg=False, spice_level=1, prep_minutes=25, photo='er4d081765186828'),
        dict(name='Chicken Fried Rice', description='Wok-tossed rice with chicken, egg and vegetables.',
             price=220, is_veg=False, spice_level=1, prep_minutes=15, photo='wuyd2h1765655837'),
    ]),
    ('Curries', [
        dict(name='Chicken Handi', description='Rich, creamy chicken curry cooked in a clay pot.',
             price=300, is_veg=False, spice_level=2, prep_minutes=20, photo='wyxwsp1486979827'),
        dict(name='Rogan Josh', description='Kashmiri lamb curry with aromatic red chillies.',
             price=360, is_veg=False, spice_level=2, prep_minutes=25, photo='vvstvq1487342592'),
        dict(name='Nutty Chicken Curry', description='Mild chicken curry in a cashew and almond gravy.',
             price=290, is_veg=False, spice_level=1, prep_minutes=20, photo='yxsurp1511304301'),
        dict(name='Matar Paneer', description='Cottage cheese and green peas in a tomato-onion gravy.',
             price=240, is_veg=True, spice_level=1, prep_minutes=15, photo='xxpqsy1511452222'),
        dict(name='Dal Fry', description='Yellow lentils tempered with garlic, cumin and ghee.',
             price=180, is_veg=True, spice_level=1, prep_minutes=12, photo='wuxrtu1483564410'),
        dict(name='Rajma Masala', description='Red kidney beans simmered in a spiced tomato gravy.',
             price=190, is_veg=True, spice_level=1, prep_minutes=15, photo='sywrsu1511463066'),
        dict(name='Baingan Bharta', description='Smoky mashed aubergine cooked with onion and tomato.',
             price=200, is_veg=True, spice_level=2, prep_minutes=15, photo='urtpqw1487341253'),
    ]),
    ('Desserts & Drinks', [
        dict(name='Jaggery Modak', description='Steamed rice dumplings filled with coconut and jaggery.',
             price=120, is_veg=True, spice_level=0, prep_minutes=5, photo='gl92ih1789802951'),
        dict(name='Mango Custard', description='Layered vanilla custard with fresh mango.',
             price=140, is_veg=True, spice_level=0, prep_minutes=5, photo='u1gisz1784732667'),
        dict(name='Mango Smoothie', description='Creamy chilled mango blended with milk.',
             price=130, is_veg=True, spice_level=0, prep_minutes=5, photo='pjbaq11784731571'),
    ]),
]

STARTER_TABLES = range(1, 11)


def seed_menu(restaurant):
    if Category.query.filter_by(restaurant_id=restaurant.id).first() is not None:
        print('Menu already has data - skipped.')
        return

    dish_count = 0
    for category_order, (category_name, dishes) in enumerate(STARTER_MENU, start=1):
        category = Category(restaurant_id=restaurant.id, name=category_name, sort_order=category_order)
        db.session.add(category)
        db.session.flush()
        for dish_order, dish in enumerate(dishes, start=1):
            db.session.add(MenuItem(
                restaurant_id=restaurant.id,
                category_id=category.id,
                name=dish['name'],
                description=dish['description'],
                price=Decimal(dish['price']),
                is_veg=dish['is_veg'],
                spice_level=dish['spice_level'],
                prep_minutes=dish['prep_minutes'],
                image_url=PHOTO.format(dish['photo']),
                sort_order=dish_order,
            ))
            dish_count += 1
    db.session.commit()
    print(f'Added {len(STARTER_MENU)} categories and {dish_count} dishes.')


def seed_tables(restaurant):
    if DiningTable.query.filter_by(restaurant_id=restaurant.id).first() is not None:
        print('Tables already exist - skipped.')
        return

    for number in STARTER_TABLES:
        db.session.add(DiningTable(restaurant_id=restaurant.id, number=number, pin=generate_table_pin(number)))
    db.session.commit()
    print(f'Added tables {STARTER_TABLES.start}-{STARTER_TABLES.stop - 1}.')


def _pick_restaurant(code):
    if code:
        restaurant = Restaurant.query.filter_by(join_code=code.upper()).first()
        if restaurant is None:
            raise SystemExit(f'No restaurant has the code {code}.')
        return restaurant
    restaurant = Restaurant.query.order_by(Restaurant.id).first()
    if restaurant is None:
        restaurant = Restaurant(name='Demo Restaurant', join_code=generate_join_code())
        db.session.add(restaurant)
        db.session.commit()
        print(f'Created "Demo Restaurant" (restaurant code {restaurant.join_code}).')
    return restaurant


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Add a starter menu and tables to a restaurant.')
    parser.add_argument('--code', help='Restaurant code of the restaurant to fill.')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        target = _pick_restaurant(args.code)
        print(f'Filling "{target.name}"...')
        seed_menu(target)
        seed_tables(target)
