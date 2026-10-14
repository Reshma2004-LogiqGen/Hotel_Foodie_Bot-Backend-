"""
Food Friend Backend - Create or reset an admin login

Usage:
    python -m app.create_admin
    python -m app.create_admin --email owner@restaurant.com --name "Owner" --restaurant "Spice Garden"
    python -m app.create_admin --email manager@restaurant.com --code K7M2QX

A new admin creates a new restaurant (--restaurant) or joins one by its restaurant code (--code).
If the email already exists, its name and password are updated and it becomes an admin.
"""

import argparse
import getpass

from app import create_app
from app.extensions import db
from app.models import ROLE_ADMIN, AdminUser, Restaurant, generate_join_code
from app.utils.validation import EMAIL_PATTERN, MIN_PASSWORD_LENGTH


def _ask(prompt, current=None):
    value = current
    while not value:
        value = input(prompt).strip()
    return value


def main():
    parser = argparse.ArgumentParser(description='Create or reset a Food Friend admin login.')
    parser.add_argument('--email')
    parser.add_argument('--name')
    parser.add_argument('--password', help='Leave out to type it privately.')
    parser.add_argument('--restaurant', help='Name of a new restaurant for a new admin.')
    parser.add_argument('--code', help='Restaurant code to join an existing restaurant.')
    args = parser.parse_args()

    email = _ask('Email: ', args.email).lower()
    if not EMAIL_PATTERN.match(email):
        raise SystemExit('That email address does not look valid.')
    name = _ask('Name: ', args.name)

    password = args.password
    if not password:
        password = getpass.getpass(f'Password (min {MIN_PASSWORD_LENGTH} characters): ')
        if password != getpass.getpass('Repeat password: '):
            raise SystemExit('Passwords do not match.')
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f'Password must be at least {MIN_PASSWORD_LENGTH} characters.')

    app = create_app()
    with app.app_context():
        admin = AdminUser.query.filter_by(email=email).first()
        created = admin is None
        if created:
            if args.code:
                restaurant = Restaurant.query.filter_by(join_code=args.code.upper()).first()
                if restaurant is None:
                    raise SystemExit(f'No restaurant has the code {args.code}.')
            else:
                restaurant = Restaurant(
                    name=_ask('Restaurant name: ', args.restaurant), join_code=generate_join_code()
                )
                db.session.add(restaurant)
            admin = AdminUser(email=email, restaurant=restaurant)
            db.session.add(admin)
        admin.name = name
        admin.role = ROLE_ADMIN
        admin.set_password(password)
        db.session.commit()
        restaurant = admin.restaurant
        print(f"Admin {'created' if created else 'updated'}: {email}")
        print(f'Restaurant: {restaurant.name} (restaurant code {restaurant.join_code})')


if __name__ == '__main__':
    main()
