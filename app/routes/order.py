"""
Food Friend Backend - Order Routes
Handles order creation and management for Chef Portal
"""

from flask import Blueprint, request, jsonify
from datetime import datetime

order_bp = Blueprint('order', __name__)

# In-memory order storage (replace with database in production)
orders = []

# Menu items for enriching order data
MENU_ITEMS = {
    1: {'name': 'Margherita Pizza', 'price': 12.99, 'emoji': '🍕'},
    2: {'name': 'Chicken Burger', 'price': 9.99, 'emoji': '🍔'},
    3: {'name': 'Caesar Salad', 'price': 8.49, 'emoji': '🥗'},
    4: {'name': 'Pasta Carbonara', 'price': 14.99, 'emoji': '🍝'},
    5: {'name': 'Fish & Chips', 'price': 13.49, 'emoji': '🐟'},
    6: {'name': 'Veggie Wrap', 'price': 7.99, 'emoji': '🌯'},
    7: {'name': 'Sushi Platter', 'price': 18.99, 'emoji': '🍣'},
    8: {'name': 'Tacos', 'price': 10.99, 'emoji': '🌮'},
    9: {'name': 'Grilled Salmon', 'price': 16.99, 'emoji': '🐠'},
    10: {'name': 'Butter Chicken', 'price': 13.99, 'emoji': '🍛'},
    11: {'name': 'Mushroom Risotto', 'price': 12.49, 'emoji': '🍚'},
    12: {'name': 'BBQ Ribs', 'price': 19.99, 'emoji': '🍖'},
    13: {'name': 'Greek Salad', 'price': 7.99, 'emoji': '🥒'},
    14: {'name': 'Chicken Wings', 'price': 11.99, 'emoji': '🍗'},
    15: {'name': 'Paneer Tikka', 'price': 10.99, 'emoji': '🧀'},
    16: {'name': 'Fruit Smoothie', 'price': 5.99, 'emoji': '🥤'},
}


def enrich_item(item):
    """Add emoji and price to item if missing"""
    item_id = item.get('id')
    if item_id and item_id in MENU_ITEMS:
        menu_item = MENU_ITEMS[item_id]
        return {
            'id': item_id,
            'name': item.get('name', menu_item['name']),
            'quantity': item.get('quantity', 1),
            'price': item.get('price', menu_item['price']),
            'emoji': item.get('emoji', menu_item['emoji'])
        }
    # Return item as-is if no match found
    return {
        'id': item.get('id', 0),
        'name': item.get('name', 'Unknown Item'),
        'quantity': item.get('quantity', 1),
        'price': item.get('price', 0),
        'emoji': item.get('emoji', '🍽️')
    }


@order_bp.route('/order', methods=['POST'])
def create_order():
    """
    Create a new order
    
    Request body:
    {
        "items": [{"id": 1, "name": "Pizza", "quantity": 2, "price": 12.99, "emoji": "🍕"}],
        "tableNumber": 5,
        "total": 25.98,
        "orderId": "ORD-ABC123"
    }
    """
    try:
        data = request.get_json()
        print(f"📦 New order received: {data}")
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Enrich items with full data
        raw_items = data.get('items', [])
        enriched_items = [enrich_item(item) for item in raw_items]
        
        # Calculate total if not provided
        total = data.get('total', 0)
        if not total:
            total = sum(item['price'] * item['quantity'] for item in enriched_items)
        
        # Create order object
        order = {
            'id': data.get('orderId', f"ORD-{datetime.now().strftime('%H%M%S')}"),
            'items': enriched_items,
            'tableNumber': data.get('tableNumber', 0),
            'total': round(total, 2),
            'status': 'confirmed',
            'createdAt': datetime.now().isoformat()
        }
        
        # Add to orders list
        orders.append(order)
        
        print(f"✅ Order created: {order['id']}")
        item_strs = [f"{i['emoji']} {i['name']} x{i['quantity']}" for i in enriched_items]
        print(f"   Items: {', '.join(item_strs)}")
        print(f"📋 Total orders in system: {len(orders)}")
        
        return jsonify({
            'success': True,
            'orderId': order['id'],
            'message': 'Order placed successfully!'
        })
        
    except Exception as e:
        print(f"❌ Order error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@order_bp.route('/orders', methods=['GET'])
def get_orders():
    """
    Get all orders (for Chef Portal)
    Returns orders sorted by creation time (newest first)
    """
    try:
        # Sort by creation time, newest first
        sorted_orders = sorted(
            orders, 
            key=lambda x: x.get('createdAt', ''), 
            reverse=True
        )
        
        print(f"📋 Returning {len(sorted_orders)} orders to Chef Portal")
        return jsonify(sorted_orders)
        
    except Exception as e:
        print(f"❌ Get orders error: {str(e)}")
        return jsonify([])


@order_bp.route('/order/<order_id>', methods=['GET'])
def get_order(order_id):
    """Get a specific order by ID"""
    try:
        order = next((o for o in orders if o['id'] == order_id), None)
        
        if order:
            return jsonify(order)
        return jsonify({'error': 'Order not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@order_bp.route('/order/<order_id>/status', methods=['PUT', 'PATCH'])
def update_order_status(order_id):
    """
    Update order status (for Chef Portal)
    
    Request body:
    {
        "status": "preparing" | "ready" | "delivered"
    }
    """
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Status required'}), 400
        
        # Valid statuses
        valid_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'delivered']
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400
        
        # Find and update order
        order = next((o for o in orders if o['id'] == order_id), None)
        
        if order:
            order['status'] = new_status
            order['updatedAt'] = datetime.now().isoformat()
            
            print(f"✅ Order {order_id} status updated to: {new_status}")
            
            return jsonify({
                'success': True,
                'orderId': order_id,
                'status': new_status
            })
        
        return jsonify({'error': 'Order not found'}), 404
        
    except Exception as e:
        print(f"❌ Status update error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@order_bp.route('/orders/clear', methods=['DELETE'])
def clear_orders():
    """Clear all orders (for testing)"""
    global orders
    orders = []
    print("🗑️ All orders cleared")
    return jsonify({'success': True, 'message': 'All orders cleared'})


@order_bp.route('/orders/stats', methods=['GET'])
def get_order_stats():
    """Get order statistics"""
    try:
        stats = {
            'total': len(orders),
            'pending': len([o for o in orders if o['status'] == 'pending']),
            'confirmed': len([o for o in orders if o['status'] == 'confirmed']),
            'preparing': len([o for o in orders if o['status'] == 'preparing']),
            'ready': len([o for o in orders if o['status'] == 'ready']),
            'delivered': len([o for o in orders if o['status'] == 'delivered'])
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500