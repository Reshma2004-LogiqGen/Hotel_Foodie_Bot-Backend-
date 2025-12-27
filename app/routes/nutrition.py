"""
Food Friend Backend - Nutrition Routes
Handles nutrition calculation and display
"""

from flask import Blueprint, request, jsonify
from app.services.nutrition_service import NutritionService

nutrition_bp = Blueprint('nutrition', __name__)
nutrition_service = NutritionService()


@nutrition_bp.route('/nutrition/generate', methods=['POST'])
def generate_nutrition():
    """
    Generate nutrition for ordered items - MAIN ENDPOINT
    Frontend calls: POST /api/nutrition/generate
    
    Request body:
    {
        "items": [
            {"name": "Margherita Pizza", "quantity": 1},
            {"name": "Caesar Salad", "quantity": 2}
        ]
    }
    """
    try:
        data = request.get_json()
        print(f"📊 Nutrition request: {data}")
        
        if not data or not data.get('items'):
            return jsonify({'error': 'No items provided'}), 400
        
        items = data.get('items', [])
        print(f"📊 Processing {len(items)} items")
        
        # Calculate nutrition
        nutrition_data = nutrition_service.calculate_nutrition(items)
        print(f"📊 Nutrition calculated successfully")
        
        return jsonify(nutrition_data)
        
    except Exception as e:
        print(f"❌ Nutrition error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return fallback data
        return jsonify({
            'items': [],
            'totals': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0, 'sugar': 0},
            'dailyPercentages': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0, 'sugar': 0},
            'healthTip': 'Enjoy your meal!',
            'error': str(e)
        })


@nutrition_bp.route('/nutrition', methods=['POST'])
def get_nutrition_post():
    """Alias for generate_nutrition"""
    return generate_nutrition()


@nutrition_bp.route('/nutrition/<int:item_id>', methods=['GET'])
def get_item_nutrition(item_id):
    """Get nutrition for a specific menu item by ID"""
    try:
        nutrition = nutrition_service.get_item_nutrition_by_id(item_id)
        if nutrition:
            return jsonify(nutrition)
        return jsonify({'error': 'Item not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@nutrition_bp.route('/nutrition', methods=['GET'])
def get_all_nutrition():
    """Get nutrition for all menu items"""
    try:
        all_nutrition = []
        for item_id in range(1, 17):
            nutrition = nutrition_service.get_item_nutrition_by_id(item_id)
            if nutrition:
                all_nutrition.append(nutrition)
        return jsonify(all_nutrition)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
