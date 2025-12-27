"""
Food Friend Backend - Nutrition Service
Handles nutrition calculations - ALWAYS returns valid data
"""

from app.services.groq_service import GroqService


class NutritionService:
    """Service for calculating and managing nutrition data"""
    
    def __init__(self):
        self.groq_service = GroqService()
        
        # Reliable fallback nutrition data with vitamins
        self.default_nutrition = {
            'Margherita Pizza': {
                'calories': 850, 'protein': 35, 'carbs': 95, 'fat': 38, 'fiber': 4, 'sugar': 8,
                'vitamins': ['Vitamin A', 'Vitamin C', 'Calcium', 'Iron']
            },
            'Chicken Burger': {
                'calories': 650, 'protein': 38, 'carbs': 45, 'fat': 32, 'fiber': 3, 'sugar': 6,
                'vitamins': ['Vitamin B12', 'Protein', 'Iron', 'Zinc']
            },
            'Caesar Salad': {
                'calories': 350, 'protein': 12, 'carbs': 18, 'fat': 28, 'fiber': 4, 'sugar': 3,
                'vitamins': ['Vitamin K', 'Vitamin A', 'Folate', 'Fiber']
            },
            'Pasta Carbonara': {
                'calories': 750, 'protein': 28, 'carbs': 85, 'fat': 35, 'fiber': 3, 'sugar': 4,
                'vitamins': ['Vitamin B12', 'Calcium', 'Iron', 'Protein']
            },
            'Fish & Chips': {
                'calories': 950, 'protein': 42, 'carbs': 88, 'fat': 48, 'fiber': 5, 'sugar': 2,
                'vitamins': ['Omega-3', 'Vitamin D', 'Protein', 'Potassium']
            },
            'Veggie Wrap': {
                'calories': 420, 'protein': 14, 'carbs': 52, 'fat': 18, 'fiber': 8, 'sugar': 6,
                'vitamins': ['Vitamin A', 'Vitamin C', 'Fiber', 'Folate']
            },
            'Sushi Platter': {
                'calories': 580, 'protein': 28, 'carbs': 75, 'fat': 12, 'fiber': 3, 'sugar': 8,
                'vitamins': ['Omega-3', 'Iodine', 'Vitamin B12', 'Selenium']
            },
            'Tacos': {
                'calories': 520, 'protein': 24, 'carbs': 48, 'fat': 26, 'fiber': 6, 'sugar': 4,
                'vitamins': ['Vitamin C', 'Vitamin A', 'Iron', 'Fiber']
            },
            'Grilled Salmon': {
                'calories': 480, 'protein': 52, 'carbs': 8, 'fat': 28, 'fiber': 2, 'sugar': 2,
                'vitamins': ['Omega-3', 'Vitamin D', 'Vitamin B12', 'Selenium']
            },
            'Butter Chicken': {
                'calories': 650, 'protein': 38, 'carbs': 35, 'fat': 42, 'fiber': 4, 'sugar': 8,
                'vitamins': ['Vitamin A', 'Vitamin B6', 'Iron', 'Protein']
            },
            'Mushroom Risotto': {
                'calories': 580, 'protein': 14, 'carbs': 78, 'fat': 24, 'fiber': 3, 'sugar': 3,
                'vitamins': ['Vitamin D', 'Vitamin B3', 'Selenium', 'Potassium']
            },
            'BBQ Ribs': {
                'calories': 1100, 'protein': 58, 'carbs': 42, 'fat': 75, 'fiber': 2, 'sugar': 28,
                'vitamins': ['Vitamin B12', 'Zinc', 'Iron', 'Protein']
            },
            'Greek Salad': {
                'calories': 280, 'protein': 8, 'carbs': 14, 'fat': 22, 'fiber': 4, 'sugar': 6,
                'vitamins': ['Vitamin K', 'Vitamin C', 'Calcium', 'Fiber']
            },
            'Chicken Wings': {
                'calories': 680, 'protein': 48, 'carbs': 8, 'fat': 52, 'fiber': 1, 'sugar': 2,
                'vitamins': ['Vitamin B6', 'Protein', 'Zinc', 'Niacin']
            },
            'Paneer Tikka': {
                'calories': 450, 'protein': 24, 'carbs': 18, 'fat': 32, 'fiber': 3, 'sugar': 5,
                'vitamins': ['Calcium', 'Vitamin B12', 'Protein', 'Phosphorus']
            },
            'Fruit Smoothie': {
                'calories': 220, 'protein': 4, 'carbs': 48, 'fat': 2, 'fiber': 4, 'sugar': 38,
                'vitamins': ['Vitamin C', 'Vitamin A', 'Potassium', 'Antioxidants']
            },
        }
        
        # Daily recommended values
        self.daily_values = {
            'calories': 2000,
            'protein': 50,
            'carbs': 300,
            'fat': 65,
            'fiber': 25,
            'sugar': 50
        }
    
    def calculate_nutrition(self, items: list) -> dict:
        """
        Calculate nutrition for a list of items
        ALWAYS returns valid data using fallback
        """
        print(f"🔢 Calculating nutrition for: {items}")
        
        # Try LLM first, fall back to static data
        try:
            llm_result = self.groq_service.generate_nutrition_data(items)
            if llm_result and 'totals' in llm_result:
                # Add daily percentages if not present
                if 'dailyPercentages' not in llm_result:
                    llm_result['dailyPercentages'] = self._calculate_percentages(llm_result['totals'])
                print("✅ Using LLM-generated nutrition data")
                return llm_result
        except Exception as e:
            print(f"⚠️ LLM nutrition failed: {e}")
        
        # Use fallback calculation
        print("📊 Using fallback nutrition data")
        return self._calculate_fallback_nutrition(items)
    
    def _calculate_fallback_nutrition(self, items: list) -> dict:
        """Calculate nutrition using fallback data - ALWAYS works"""
        result_items = []
        totals = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0, 'sugar': 0}
        
        for item in items:
            name = item.get('name', '')
            quantity = item.get('quantity', 1)
            
            print(f"  Processing: {name} x{quantity}")
            
            # Find matching nutrition data
            nutrition = self._find_nutrition(name)
            
            # Calculate for quantity
            item_nutrition = {
                'name': name,
                'quantity': quantity,
                'calories': nutrition['calories'] * quantity,
                'protein': nutrition['protein'] * quantity,
                'carbs': nutrition['carbs'] * quantity,
                'fat': nutrition['fat'] * quantity,
                'fiber': nutrition['fiber'] * quantity,
                'sugar': nutrition['sugar'] * quantity,
                'vitamins': nutrition.get('vitamins', ['Various Nutrients'])
            }
            result_items.append(item_nutrition)
            
            # Add to totals
            for key in totals:
                totals[key] += item_nutrition[key]
        
        # Calculate daily percentages
        daily_percentages = self._calculate_percentages(totals)
        
        # Generate health tip
        health_tip = self._generate_health_tip(totals, daily_percentages)
        
        return {
            'items': result_items,
            'totals': totals,
            'dailyPercentages': daily_percentages,
            'healthTip': health_tip
        }
    
    def _find_nutrition(self, name: str) -> dict:
        """Find nutrition data for an item by name"""
        # Exact match
        if name in self.default_nutrition:
            return self.default_nutrition[name]
        
        # Partial match
        name_lower = name.lower()
        for key in self.default_nutrition:
            if key.lower() in name_lower or name_lower in key.lower():
                return self.default_nutrition[key]
        
        # Default fallback
        return {
            'calories': 500, 'protein': 20, 'carbs': 50, 
            'fat': 20, 'fiber': 3, 'sugar': 10,
            'vitamins': ['Various Nutrients']
        }
    
    def _calculate_percentages(self, totals: dict) -> dict:
        """Calculate daily value percentages"""
        return {
            key: round((totals[key] / self.daily_values[key]) * 100, 1)
            for key in self.daily_values
        }
    
    def _generate_health_tip(self, totals: dict, percentages: dict) -> str:
        """Generate a health tip based on the nutrition"""
        if percentages['protein'] > 50:
            return "Great protein choice! 💪 Perfect for muscle recovery."
        elif percentages['fiber'] > 30:
            return "Nice fiber content! 🥗 Good for digestion."
        elif percentages['sugar'] > 50:
            return "Sweet choice! 🍬 Balance with some veggies next time."
        elif percentages['calories'] > 60:
            return "A hearty meal! 🏃 Perfect for an active day."
        elif percentages['fat'] > 50:
            return "Rich and satisfying! 😋 Enjoy every bite."
        else:
            return "Enjoy your balanced meal! 😊 Great choices!"
    
    def get_item_nutrition_by_id(self, item_id: int) -> dict:
        """Get nutrition for a specific menu item by ID"""
        menu_items = {
            1: 'Margherita Pizza', 2: 'Chicken Burger', 3: 'Caesar Salad',
            4: 'Pasta Carbonara', 5: 'Fish & Chips', 6: 'Veggie Wrap',
            7: 'Sushi Platter', 8: 'Tacos', 9: 'Grilled Salmon',
            10: 'Butter Chicken', 11: 'Mushroom Risotto', 12: 'BBQ Ribs',
            13: 'Greek Salad', 14: 'Chicken Wings', 15: 'Paneer Tikka',
            16: 'Fruit Smoothie'
        }
        
        name = menu_items.get(item_id)
        if name and name in self.default_nutrition:
            return {'id': item_id, 'name': name, **self.default_nutrition[name]}
        return None
