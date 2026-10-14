"""
Food Friend Backend - In-place upgrade for databases made by older versions.
db.create_all() only creates missing tables; it never changes existing ones.
"""

import secrets

from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateIndex, CreateTable

from app.extensions import db
from app.models import TABLE_PIN_LENGTH, Category, DiningTable, generate_join_code
from app.timeutil import local_now

DEFAULT_RESTAURANT_NAME = 'My Restaurant'

# Tables that only need a restaurant_id column added.
TABLES_GAINING_RESTAURANT = ('admin_users', 'menu_items', 'orders')
# Tables whose unique constraints change (unique per restaurant), so they are rebuilt.
TABLES_TO_REBUILD = (Category.__table__, DiningTable.__table__)


def _columns(table_name):
    return {c['name'] for c in inspect(db.engine).get_columns(table_name)}


def _pins_for(numbers):
    """A table PIN for each table number, keeping (number, PIN) unique."""
    used = set()
    pins = []
    for number in numbers:
        while True:
            pin = ''.join(secrets.choice('0123456789') for _ in range(TABLE_PIN_LENGTH))
            if (number, pin) not in used:
                used.add((number, pin))
                pins.append(pin)
                break
    return pins


def _rebuild_with_restaurant(cursor, table, restaurant_id):
    cursor.execute(f'SELECT * FROM {table.name}')
    old_columns = [d[0] for d in cursor.description]
    rows = cursor.fetchall()

    cursor.execute(f'DROP TABLE {table.name}')
    cursor.execute(str(CreateTable(table).compile(db.engine)))
    for index in table.indexes:
        cursor.execute(str(CreateIndex(index).compile(db.engine)))

    kept = [c for c in old_columns if c in table.columns]
    values = [tuple(row[old_columns.index(c)] for c in kept) + (restaurant_id,) for row in rows]
    insert_columns = kept + ['restaurant_id']
    if 'pin' in table.columns and 'pin' not in old_columns:
        pins = _pins_for(row[old_columns.index('number')] for row in rows)
        values = [v + (pin,) for v, pin in zip(values, pins)]
        insert_columns.append('pin')
    placeholders = ', '.join('?' for _ in insert_columns)
    cursor.executemany(
        f'INSERT INTO {table.name} ({", ".join(insert_columns)}) VALUES ({placeholders})',
        values,
    )


def _has_rows(cursor, table_name):
    cursor.execute(f'SELECT 1 FROM {table_name} LIMIT 1')
    return cursor.fetchone() is not None


def upgrade_schema():
    _move_to_restaurants()
    _add_table_pins()
    _add_order_nutrition()


def _add_order_nutrition():
    if 'nutrition' in _columns('orders'):
        return
    with db.engine.begin() as conn:
        conn.execute(text('ALTER TABLE orders ADD COLUMN nutrition JSON'))
    print('✅ Database upgraded: orders can now keep their nutrition summary.')


def _add_table_pins():
    """Give every existing table the PIN customers type when they can't scan."""
    if 'pin' in _columns('dining_tables'):
        return
    with db.engine.begin() as conn:
        rows = conn.execute(text('SELECT id, number FROM dining_tables')).all()
        conn.execute(text(
            f"ALTER TABLE dining_tables ADD COLUMN pin VARCHAR({TABLE_PIN_LENGTH}) NOT NULL DEFAULT ''"
        ))
        pins = _pins_for(number for _, number in rows)
        for (table_id, _), pin in zip(rows, pins):
            conn.execute(text('UPDATE dining_tables SET pin = :pin WHERE id = :id'), {'pin': pin, 'id': table_id})
        conn.execute(text('CREATE UNIQUE INDEX ix_dining_tables_number_pin ON dining_tables (number, pin)'))
    print(f'✅ Database upgraded: added PINs to {len(rows)} tables.')


def _move_to_restaurants():
    """Move a single-restaurant database to restaurants, keeping all existing data."""
    if 'restaurant_id' in _columns('categories'):
        return

    admin_columns = _columns('admin_users')
    columns_by_table = {name: _columns(name) for name in TABLES_GAINING_RESTAURANT}
    join_code = generate_join_code()
    db.session.remove()

    connection = db.engine.raw_connection()
    sqlite_connection = connection.driver_connection
    previous_isolation = sqlite_connection.isolation_level
    sqlite_connection.isolation_level = None
    cursor = sqlite_connection.cursor()
    try:
        # Foreign keys must be off while tables referenced by others are rebuilt.
        cursor.execute('PRAGMA foreign_keys=OFF')
        cursor.execute('BEGIN')

        if 'role' not in admin_columns:
            cursor.execute("ALTER TABLE admin_users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'admin'")
        if 'is_approved' in admin_columns:
            cursor.execute('ALTER TABLE admin_users DROP COLUMN is_approved')

        restaurant_id = None
        legacy_tables = TABLES_GAINING_RESTAURANT + tuple(t.name for t in TABLES_TO_REBUILD)
        if any(_has_rows(cursor, name) for name in legacy_tables):
            cursor.execute(
                'INSERT INTO restaurants (name, join_code, created_at) VALUES (?, ?, ?)',
                (DEFAULT_RESTAURANT_NAME, join_code, str(local_now())),
            )
            restaurant_id = cursor.lastrowid

        for name in TABLES_GAINING_RESTAURANT:
            if 'restaurant_id' not in columns_by_table[name]:
                cursor.execute(
                    f'ALTER TABLE {name} ADD COLUMN restaurant_id INTEGER '
                    'REFERENCES restaurants (id) ON DELETE CASCADE'
                )
                cursor.execute(f'CREATE INDEX IF NOT EXISTS ix_{name}_restaurant_id ON {name} (restaurant_id)')
                cursor.execute(f'UPDATE {name} SET restaurant_id = ?', (restaurant_id,))

        for table in TABLES_TO_REBUILD:
            _rebuild_with_restaurant(cursor, table, restaurant_id)

        cursor.execute('COMMIT')
    except Exception:
        cursor.execute('ROLLBACK')
        raise
    finally:
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()
        sqlite_connection.isolation_level = previous_isolation
        connection.close()

    print(f'✅ Database upgraded: existing data moved into "{DEFAULT_RESTAURANT_NAME}".')
