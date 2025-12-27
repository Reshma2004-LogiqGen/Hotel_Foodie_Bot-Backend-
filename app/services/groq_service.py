"""
Food Friend Backend - GROQ Service
Handles all LLM API calls using GROQ
"""

import os
from groq import Groq


class GroqService:
    """Service for interacting with GROQ API"""
    
    def __init__(self):
        self.api_key = os.getenv('GROQ_API_KEY')
        if not self.api_key:
            print("⚠️ WARNING: GROQ_API_KEY not found in environment!")
            print("   Please create a .env file with: GROQ_API_KEY=your_key_here")
        
        try:
            self.client = Groq(api_key=self.api_key)
            print("✅ GROQ client initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize GROQ client: {e}")
            self.client = None
        
        self.model = "llama-3.3-70b-versatile"
    
    def generate_chat_response(self, system_prompt: str, user_message: str, 
                                conversation_history: list = None) -> str:
        """
        Generate a chat response using GROQ
        
        Args:
            system_prompt: The persona/system instructions
            user_message: The user's message
            conversation_history: Previous messages in the conversation
        
        Returns:
            The AI generated response (short, 2 sentences max)
        """
        if not self.client:
            print("❌ GROQ client not available")
            return "Hey there! What's up? 😊"
        
        try:
            # Build messages array
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history (limit to last 4 messages)
            if conversation_history:
                for msg in conversation_history[-4:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            print(f"🤖 Sending to GROQ: {len(messages)} messages")
            
            # Call GROQ API with 50 tokens limit
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=50,  # 50 tokens for short responses
                temperature=0.8
            )
            
            result = response.choices[0].message.content.strip()
            print(f"✅ GROQ response: {result}")
            
            return result
            
        except Exception as e:
            print(f"❌ GROQ API error: {str(e)}")
            import traceback
            traceback.print_exc()
            return "Oops! What were we talking about? 😅"
    
    def generate_nutrition_data(self, items: list) -> dict:
        """
        Generate nutrition data for food items using LLM
        
        Args:
            items: List of food items with name and quantity
        
        Returns:
            Dictionary with nutrition information
        """
        if not self.client:
            return None
        
        try:
            items_text = ", ".join([f"{item.get('name', 'food')} x{item.get('quantity', 1)}" 
                                    for item in items])
            
            prompt = f"""Calculate nutrition for these food items: {items_text}

Return ONLY a JSON object (no markdown, no explanation) in this exact format:
{{
  "items": [
    {{
      "name": "Item Name",
      "quantity": 1,
      "calories": 500,
      "protein": 20,
      "carbs": 50,
      "fat": 25,
      "fiber": 3,
      "sugar": 8,
      "vitamins": ["Vitamin A", "Vitamin C", "Iron"]
    }}
  ],
  "totals": {{
    "calories": 500,
    "protein": 20,
    "carbs": 50,
    "fat": 25,
    "fiber": 3,
    "sugar": 8
  }},
  "healthTip": "A short health tip about this meal"
}}"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a nutrition expert. Return ONLY valid JSON, no markdown or extra text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.2
            )
            
            result = response.choices[0].message.content.strip()
            
            # Clean up response - remove markdown if present
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
                result = result.strip()
            
            import json
            return json.loads(result)
            
        except Exception as e:
            print(f"❌ Nutrition generation error: {str(e)}")
            return None