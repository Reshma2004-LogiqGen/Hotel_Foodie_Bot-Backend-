"""
Food Friend Backend - Admin menu management routes
Categories, dishes and dish photo uploads
"""

import uuid
from datetime import timedelta

from flask import Blueprint, g, jsonify, request
from sqlalchemy import func

from app.auth import admin_required
from app.extensions import db
from app.models import Category, MenuItem, OrderItem, UploadedImage
from app.timeutil import local_now
from app.utils.validation import (
    ValidationError,
    clean_bool,
    clean_image_url,
    clean_int,
    clean_price,
    clean_text,
    get_json_body,
)

admin_menu_bp = Blueprint('admin_menu', __name__)

IMAGE_SIGNATURES = {
    'jpg': lambda head: head.startswith(b'\xff\xd8\xff'),
    'png': lambda head: head.startswith(b'\x89PNG\r\n\x1a\n'),
    'webp': lambda head: head[:4] == b'RIFF' and head[8:12] == b'WEBP',
}
CONTENT_TYPES = {'jpg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp'}
# A photo no dish uses after this long was replaced, removed or never saved.
UNUSED_PHOTO_HOURS = 24


def _error(message, status=400):
    return jsonify({'error': message}), status


def _active_item_counts():
    rows = (
        db.session.query(MenuItem.category_id, func.count(MenuItem.id))
        .filter(MenuItem.restaurant_id == g.restaurant_id, MenuItem.is_archived.is_(False))
        .group_by(MenuItem.category_id)
        .all()
    )
    return dict(rows)


def _own_category(category_id):
    category = db.session.get(Category, category_id)
    return category if category is not None and category.restaurant_id == g.restaurant_id else None


def _get_category_or_404(category_id):
    category = _own_category(category_id)
    if category is None:
        return None, _error('Category not found.', 404)
    return category, None


def _get_item_or_404(item_id):
    item = db.session.get(MenuItem, item_id)
    if item is None or item.is_archived or item.restaurant_id != g.restaurant_id:
        return None, _error('Dish not found.', 404)
    return item, None


def _name_taken(name, exclude_id=None):
    query = Category.query.filter(
        Category.restaurant_id == g.restaurant_id, func.lower(Category.name) == name.lower()
    )
    if exclude_id is not None:
        query = query.filter(Category.id != exclude_id)
    return db.session.query(query.exists()).scalar()


# ==================== CATEGORIES ====================

@admin_menu_bp.route('/admin/categories', methods=['GET'])
@admin_required
def list_categories():
    counts = _active_item_counts()
    categories = (
        Category.query.filter_by(restaurant_id=g.restaurant_id)
        .order_by(Category.sort_order, Category.id)
        .all()
    )
    return jsonify([c.to_dict(item_count=counts.get(c.id, 0)) for c in categories])


@admin_menu_bp.route('/admin/categories', methods=['POST'])
@admin_required
def create_category():
    try:
        data = get_json_body(request)
        name = clean_text(data.get('name'), 'Category name', 60, required=True)
    except ValidationError as e:
        return _error(e.message)

    if _name_taken(name):
        return _error('A category with this name already exists.', 409)

    max_order = (
        db.session.query(func.max(Category.sort_order))
        .filter(Category.restaurant_id == g.restaurant_id)
        .scalar()
    )
    category = Category(restaurant_id=g.restaurant_id, name=name, sort_order=(max_order or 0) + 1)
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict(item_count=0)), 201


@admin_menu_bp.route('/admin/categories/<int:category_id>', methods=['PATCH'])
@admin_required
def update_category(category_id):
    category, error = _get_category_or_404(category_id)
    if error:
        return error

    try:
        data = get_json_body(request)
        if 'name' in data:
            name = clean_text(data['name'], 'Category name', 60, required=True)
            if _name_taken(name, exclude_id=category.id):
                return _error('A category with this name already exists.', 409)
            category.name = name
        if 'isVisible' in data:
            category.is_visible = clean_bool(data['isVisible'], 'Visible')
    except ValidationError as e:
        return _error(e.message)

    db.session.commit()
    return jsonify(category.to_dict(item_count=_active_item_counts().get(category.id, 0)))


@admin_menu_bp.route('/admin/categories/order', methods=['PUT'])
@admin_required
def reorder_categories():
    try:
        data = get_json_body(request)
        ids = data.get('ids')
        if not isinstance(ids, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in ids):
            raise ValidationError('ids must be a list of category ids.')
    except ValidationError as e:
        return _error(e.message)

    categories = {c.id: c for c in Category.query.filter_by(restaurant_id=g.restaurant_id).all()}
    if len(ids) != len(set(ids)) or set(ids) != set(categories):
        return _error('ids must contain every category exactly once.')

    for position, category_id in enumerate(ids, start=1):
        categories[category_id].sort_order = position
    db.session.commit()
    return list_categories()


@admin_menu_bp.route('/admin/categories/<int:category_id>', methods=['DELETE'])
@admin_required
def delete_category(category_id):
    """Delete a category. With ?withDishes=true its dishes are deleted too."""
    category, error = _get_category_or_404(category_id)
    if error:
        return error

    active_items = MenuItem.query.filter_by(category_id=category.id, is_archived=False).all()
    if active_items and request.args.get('withDishes') != 'true':
        noun = 'dish' if len(active_items) == 1 else 'dishes'
        return _error(f'This category still has {len(active_items)} {noun}.', 409)

    for item in active_items:
        _remove_item(item)
    MenuItem.query.filter_by(category_id=category.id).update({'category_id': None})
    db.session.delete(category)
    db.session.commit()
    return jsonify({'success': True})


# ==================== DISHES ====================

def _apply_item_fields(item, data, creating):
    """Validate the given fields and copy them onto the item."""
    def present(key):
        return creating or key in data

    if present('name'):
        item.name = clean_text(data.get('name'), 'Dish name', 120, required=True)
    if present('description'):
        item.description = clean_text(data.get('description'), 'Description', 500)
    if present('price'):
        item.price = clean_price(data.get('price'))
    if present('categoryId'):
        category_id = clean_int(data.get('categoryId'), 'Category', 1, 2**31 - 1)
        if _own_category(category_id) is None:
            raise ValidationError('Choose a valid category.')
        item.category_id = category_id
    if 'isVeg' in data:
        item.is_veg = clean_bool(data['isVeg'], 'Veg')
    if 'spiceLevel' in data:
        item.spice_level = clean_int(data['spiceLevel'], 'Spice level', 0, 3)
    if 'prepMinutes' in data:
        item.prep_minutes = clean_int(data['prepMinutes'], 'Preparation time', 1, 180)
    if 'imageUrl' in data:
        item.image_url = clean_image_url(data['imageUrl'])
    if 'isAvailable' in data:
        item.is_available = clean_bool(data['isAvailable'], 'Available')

    nutrition = data.get('nutrition')
    if nutrition is not None:
        if not isinstance(nutrition, dict):
            raise ValidationError('Nutrition must be an object.')
        for key, column, maximum in (
            ('calories', 'calories', 5000),
            ('protein', 'protein_g', 500),
            ('carbs', 'carbs_g', 1000),
            ('fat', 'fat_g', 500),
        ):
            if key in nutrition:
                setattr(item, column, clean_int(nutrition[key], key.capitalize(), 0, maximum, required=False))


@admin_menu_bp.route('/admin/items', methods=['GET'])
@admin_required
def list_items():
    items = (
        MenuItem.query.filter(MenuItem.restaurant_id == g.restaurant_id, MenuItem.is_archived.is_(False))
        .order_by(MenuItem.sort_order, MenuItem.id)
        .all()
    )
    return jsonify([item.to_dict() for item in items])


@admin_menu_bp.route('/admin/items', methods=['POST'])
@admin_required
def create_item():
    item = MenuItem(restaurant_id=g.restaurant_id)
    try:
        _apply_item_fields(item, get_json_body(request), creating=True)
    except ValidationError as e:
        return _error(e.message)

    max_order = (
        db.session.query(func.max(MenuItem.sort_order))
        .filter(MenuItem.category_id == item.category_id)
        .scalar()
    )
    item.sort_order = (max_order or 0) + 1
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@admin_menu_bp.route('/admin/items/<int:item_id>', methods=['PATCH'])
@admin_required
def update_item(item_id):
    item, error = _get_item_or_404(item_id)
    if error:
        return error

    try:
        _apply_item_fields(item, get_json_body(request), creating=False)
    except ValidationError as e:
        db.session.rollback()
        return _error(e.message)

    db.session.commit()
    return jsonify(item.to_dict())


def _remove_item(item):
    """Dishes that were ordered are archived so past orders keep their link; others are deleted."""
    was_ordered = db.session.query(
        OrderItem.query.filter_by(menu_item_id=item.id).exists()
    ).scalar()
    if was_ordered:
        item.is_archived = True
        item.is_available = False
    else:
        db.session.delete(item)


@admin_menu_bp.route('/admin/items/<int:item_id>', methods=['DELETE'])
@admin_required
def delete_item(item_id):
    item, error = _get_item_or_404(item_id)
    if error:
        return error

    _remove_item(item)
    db.session.commit()
    return jsonify({'success': True})


# ==================== PHOTO UPLOAD ====================

def _delete_unused_photos():
    cutoff = local_now() - timedelta(hours=UNUSED_PHOTO_HOURS)
    used = {
        url.rsplit('/', 1)[-1]
        for (url,) in db.session.query(MenuItem.image_url).filter(
            MenuItem.restaurant_id == g.restaurant_id, MenuItem.image_url.like('/uploads/%')
        )
    }
    old_photos = db.session.query(UploadedImage.id, UploadedImage.filename).filter(
        UploadedImage.restaurant_id == g.restaurant_id, UploadedImage.created_at < cutoff
    )
    unused_ids = [photo_id for photo_id, filename in old_photos if filename not in used]
    if unused_ids:
        UploadedImage.query.filter(UploadedImage.id.in_(unused_ids)).delete(synchronize_session=False)


@admin_menu_bp.route('/admin/uploads', methods=['POST'])
@admin_required
def upload_image():
    file = request.files.get('file')
    if file is None or not file.filename:
        return _error('Choose an image to upload.')

    extension = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if extension == 'jpeg':
        extension = 'jpg'
    check_signature = IMAGE_SIGNATURES.get(extension)
    data = file.read()
    if check_signature is None or not check_signature(data[:16]):
        return _error('Only JPG, PNG or WEBP images are allowed.')

    _delete_unused_photos()
    filename = f'{uuid.uuid4().hex}.{extension}'
    db.session.add(UploadedImage(
        restaurant_id=g.restaurant_id, filename=filename, content_type=CONTENT_TYPES[extension], data=data,
    ))
    db.session.commit()
    return jsonify({'url': f'/uploads/{filename}'}), 201
