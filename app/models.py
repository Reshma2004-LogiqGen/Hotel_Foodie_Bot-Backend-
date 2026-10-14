"""
Food Friend Backend - Database Models
"""

import secrets

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.timeutil import iso as _iso, local_now


def generate_table_code():
    return secrets.token_urlsafe(6)


TABLE_PIN_LENGTH = 4


def generate_table_pin(number):
    """A short PIN printed on the table card. Table number + PIN is unique across all restaurants."""
    while True:
        pin = ''.join(secrets.choice('0123456789') for _ in range(TABLE_PIN_LENGTH))
        if DiningTable.query.filter_by(number=number, pin=pin).first() is None:
            return pin


JOIN_CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
JOIN_CODE_LENGTH = 6


def generate_join_code():
    """A short code staff type in to join a restaurant. Unique across restaurants."""
    while True:
        code = ''.join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(JOIN_CODE_LENGTH))
        if Restaurant.query.filter_by(join_code=code).first() is None:
            return code


ROLE_ADMIN = 'admin'
ROLE_CHEF = 'chef'
STAFF_ROLES = (ROLE_ADMIN, ROLE_CHEF)

ORDER_STATUSES = ('received', 'preparing', 'ready', 'served')


def _restaurant_fk():
    return db.Column(
        db.Integer, db.ForeignKey('restaurants.id', ondelete='CASCADE'), nullable=False, index=True
    )


class Restaurant(db.Model):
    __tablename__ = 'restaurants'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    join_code = db.Column(db.String(12), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)

    def to_dict(self, include_code=False):
        data = {'id': self.id, 'name': self.name}
        if include_code:
            data['joinCode'] = self.join_code
        return data


class AdminUser(db.Model):
    """A staff login: restaurant admin or chef."""
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = _restaurant_fk()
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default=ROLE_ADMIN, nullable=False)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    last_login_at = db.Column(db.DateTime)

    restaurant = db.relationship('Restaurant')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'restaurant': self.restaurant.to_dict() if self.restaurant else None,
            'createdAt': _iso(self.created_at),
            'lastLoginAt': _iso(self.last_login_at),
        }


class Category(db.Model):
    __tablename__ = 'categories'
    __table_args__ = (db.UniqueConstraint('restaurant_id', 'name'),)

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = _restaurant_fk()
    name = db.Column(db.String(60), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)

    items = db.relationship('MenuItem', back_populates='category', lazy='select')

    def to_dict(self, item_count=None):
        data = {
            'id': self.id,
            'name': self.name,
            'sortOrder': self.sort_order,
            'isVisible': self.is_visible,
        }
        if item_count is not None:
            data['itemCount'] = item_count
        return data


class MenuItem(db.Model):
    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = _restaurant_fk()
    category_id = db.Column(
        db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), index=True
    )
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500), default='', nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    is_veg = db.Column(db.Boolean, default=True, nullable=False)
    spice_level = db.Column(db.Integer, default=0, nullable=False)
    prep_minutes = db.Column(db.Integer, default=15, nullable=False)
    image_url = db.Column(db.String(500))
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    calories = db.Column(db.Integer)
    protein_g = db.Column(db.Integer)
    carbs_g = db.Column(db.Integer)
    fat_g = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    category = db.relationship('Category', back_populates='items')

    def to_dict(self):
        return {
            'id': self.id,
            'categoryId': self.category_id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'isVeg': self.is_veg,
            'spiceLevel': self.spice_level,
            'prepMinutes': self.prep_minutes,
            'imageUrl': self.image_url,
            'isAvailable': self.is_available,
            'sortOrder': self.sort_order,
            'nutrition': {
                'calories': self.calories,
                'protein': self.protein_g,
                'carbs': self.carbs_g,
                'fat': self.fat_g,
            },
        }


class DiningTable(db.Model):
    __tablename__ = 'dining_tables'
    __table_args__ = (
        db.UniqueConstraint('restaurant_id', 'number'),
        db.Index('ix_dining_tables_number_pin', 'number', 'pin', unique=True),
    )

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = _restaurant_fk()
    number = db.Column(db.Integer, nullable=False, index=True)
    code = db.Column(db.String(32), nullable=False, default=generate_table_code, index=True)
    pin = db.Column(db.String(TABLE_PIN_LENGTH), nullable=False)

    restaurant = db.relationship('Restaurant')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)

    scans = db.relationship(
        'TableScan', back_populates='table', cascade='all, delete-orphan', passive_deletes=True
    )

    def to_dict(self, scans_today=0, total_scans=0, last_scanned_at=None):
        return {
            'id': self.id,
            'number': self.number,
            'code': self.code,
            'pin': self.pin,
            'isActive': self.is_active,
            'scansToday': scans_today,
            'totalScans': total_scans,
            'lastScannedAt': _iso(last_scanned_at),
        }


class TableScan(db.Model):
    __tablename__ = 'table_scans'

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(
        db.Integer, db.ForeignKey('dining_tables.id', ondelete='CASCADE'), nullable=False, index=True
    )
    scanned_at = db.Column(db.DateTime, default=local_now, nullable=False, index=True)

    table = db.relationship('DiningTable', back_populates='scans')


class UploadedImage(db.Model):
    """A dish photo, kept in the database so it survives hosts that wipe their disk on every restart."""
    __tablename__ = 'uploaded_images'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = _restaurant_fk()
    filename = db.Column(db.String(64), unique=True, nullable=False)
    content_type = db.Column(db.String(40), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False)


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = _restaurant_fk()
    order_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    table_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='received', nullable=False, index=True)
    notes = db.Column(db.String(500), default='', nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    # AI nutrition summary, worked out once per order.
    nutrition = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=local_now, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=local_now, onupdate=local_now, nullable=False)

    restaurant = db.relationship('Restaurant')
    items = db.relationship(
        'OrderItem', back_populates='order', cascade='all, delete-orphan', passive_deletes=True,
        order_by='OrderItem.id',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'orderNumber': self.order_number,
            'tableNumber': self.table_number,
            'status': self.status,
            'notes': self.notes,
            'total': float(self.total),
            'createdAt': _iso(self.created_at),
            'updatedAt': _iso(self.updated_at),
            'items': [item.to_dict() for item in self.items],
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True
    )
    menu_item_id = db.Column(
        db.Integer, db.ForeignKey('menu_items.id', ondelete='SET NULL'), index=True
    )
    name = db.Column(db.String(120), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(300), default='', nullable=False)

    order = db.relationship('Order', back_populates='items')
    menu_item = db.relationship('MenuItem')

    def to_dict(self):
        return {
            'id': self.id,
            'menuItemId': self.menu_item_id,
            'name': self.name,
            'quantity': self.quantity,
            'unitPrice': float(self.unit_price),
            'notes': self.notes,
        }
