"""
Food Friend Backend - Admin table and QR code routes
"""

from datetime import datetime, time

from flask import Blueprint, g, jsonify, request
from sqlalchemy import case, func

from app.auth import admin_required
from app.extensions import db
from app.models import DiningTable, TableScan, generate_table_code, generate_table_pin
from app.timeutil import local_now
from app.utils.validation import ValidationError, clean_bool, clean_int, get_json_body

admin_tables_bp = Blueprint('admin_tables', __name__)

MAX_TABLE_NUMBER = 999
MAX_TABLES_PER_REQUEST = 100


def _error(message, status=400):
    return jsonify({'error': message}), status


def _scan_stats():
    """Return {table_id: (scans_today, total_scans, last_scanned_at)}."""
    start_of_today = datetime.combine(local_now().date(), time.min)
    rows = (
        db.session.query(
            TableScan.table_id,
            func.sum(case((TableScan.scanned_at >= start_of_today, 1), else_=0)),
            func.count(TableScan.id),
            func.max(TableScan.scanned_at),
        )
        .join(DiningTable, DiningTable.id == TableScan.table_id)
        .filter(DiningTable.restaurant_id == g.restaurant_id)
        .group_by(TableScan.table_id)
        .all()
    )
    return {table_id: (int(today or 0), total, last) for table_id, today, total, last in rows}


def _serialize(table, stats):
    scans_today, total_scans, last_scanned_at = stats.get(table.id, (0, 0, None))
    return table.to_dict(scans_today, total_scans, last_scanned_at)


def _get_table_or_404(table_id):
    table = db.session.get(DiningTable, table_id)
    if table is None or table.restaurant_id != g.restaurant_id:
        return None, _error('Table not found.', 404)
    return table, None


@admin_tables_bp.route('/admin/tables', methods=['GET'])
@admin_required
def list_tables():
    stats = _scan_stats()
    tables = DiningTable.query.filter_by(restaurant_id=g.restaurant_id).order_by(DiningTable.number).all()
    return jsonify([_serialize(t, stats) for t in tables])


@admin_tables_bp.route('/admin/tables', methods=['POST'])
@admin_required
def create_tables():
    try:
        data = get_json_body(request)
        start = clean_int(data.get('start'), 'From table', 1, MAX_TABLE_NUMBER)
        end = clean_int(data.get('end', start), 'To table', 1, MAX_TABLE_NUMBER)
    except ValidationError as e:
        return _error(e.message)

    if end < start:
        return _error('"To table" must be greater than or equal to "From table".')
    if end - start + 1 > MAX_TABLES_PER_REQUEST:
        return _error(f'You can add up to {MAX_TABLES_PER_REQUEST} tables at a time.')

    existing = {
        number for (number,) in db.session.query(DiningTable.number)
        .filter(DiningTable.restaurant_id == g.restaurant_id, DiningTable.number.between(start, end))
        .all()
    }
    created = [n for n in range(start, end + 1) if n not in existing]
    for number in created:
        db.session.add(DiningTable(restaurant_id=g.restaurant_id, number=number, pin=generate_table_pin(number)))
    db.session.commit()

    return jsonify({'created': created, 'skipped': sorted(existing)}), 201


@admin_tables_bp.route('/admin/tables/<int:table_id>', methods=['PATCH'])
@admin_required
def update_table(table_id):
    table, error = _get_table_or_404(table_id)
    if error:
        return error

    try:
        data = get_json_body(request)
        if 'isActive' in data:
            table.is_active = clean_bool(data['isActive'], 'Active')
    except ValidationError as e:
        return _error(e.message)

    db.session.commit()
    return jsonify(_serialize(table, _scan_stats()))


@admin_tables_bp.route('/admin/tables/<int:table_id>/regenerate-code', methods=['POST'])
@admin_required
def regenerate_code(table_id):
    table, error = _get_table_or_404(table_id)
    if error:
        return error

    table.code = generate_table_code()
    table.pin = generate_table_pin(table.number)
    db.session.commit()
    return jsonify(_serialize(table, _scan_stats()))


@admin_tables_bp.route('/admin/tables/<int:table_id>', methods=['DELETE'])
@admin_required
def delete_table(table_id):
    table, error = _get_table_or_404(table_id)
    if error:
        return error

    db.session.delete(table)
    db.session.commit()
    return jsonify({'success': True})
