"""
Food Friend Backend - Chat Routes
Handles all chat-related API endpoints
STRICT: All responses must be 2 SHORT sentences for mobile
"""

from flask import Blueprint, request, jsonify
from app.services.groq_service import GroqService
from app.prompts.personas import get_persona_prompt, get_lover_prompt, get_full_prompt

chat_bp = Blueprint('chat', __name__)
groq_service = GroqService()


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint - Returns 2 SHORT sentences only
    """
    try:
        data = request.get_json()
        print(f"📨 Chat request received")
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        message = data.get('message', '')
        persona = data.get('persona', 'friend')
        lover_config = data.get('loverConfig')
        order_context = data.get('orderContext')
        conversation_history = data.get('conversationHistory', [])
        
        # Get the appropriate system prompt
        if persona == 'lover' and lover_config:
            system_prompt = get_lover_prompt(
                lover_config.get('gender', 'other'),
                lover_config.get('relationshipStatus', 'single')
            )
        else:
            system_prompt = get_persona_prompt(persona)
        
        # Add strict length requirement
        system_prompt += "\n\n⚠️ CRITICAL: Reply in EXACTLY 2 SHORT sentences! Max 15 words total! No exceptions!"
        
        # Add order context
        if order_context:
            items_str = ", ".join([f"{item.get('name', 'item')}" 
                                   for item in order_context.get('items', [])])
            system_prompt += f"\n\nThey ordered: {items_str}"
        
        # Handle initial greeting
        if message == 'START_CONVERSATION':
            message = "Say a quick 2-sentence hello!"
        
        # Generate response using GROQ
        response = groq_service.generate_chat_response(
            system_prompt=system_prompt,
            user_message=message,
            conversation_history=conversation_history
        )
        
        print(f"✅ Chat response: {response}")
        
        return jsonify({'response': response})
        
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'response': "Hey! What's up? 😅",
            'error': str(e)
        }), 200


@chat_bp.route('/chat/greeting', methods=['POST'])
def get_greeting():
    """
    Get initial greeting - 2 SHORT sentences only
    """
    try:
        data = request.get_json()
        persona = data.get('persona', 'friend')
        order_context = data.get('orderContext')
        
        system_prompt = get_persona_prompt(persona)
        system_prompt += "\n\n⚠️ CRITICAL: Reply in EXACTLY 2 SHORT sentences! Max 15 words!"
        
        if order_context:
            items_str = ", ".join([f"{item.get('name', 'item')}" 
                                   for item in order_context.get('items', [])])
            greeting_message = f"Say quick hello! They ordered: {items_str}"
        else:
            greeting_message = "Say a quick 2-sentence hello!"
        
        response = groq_service.generate_chat_response(
            system_prompt=system_prompt,
            user_message=greeting_message,
            conversation_history=[]
        )
        
        return jsonify({'response': response})
        
    except Exception as e:
        print(f"❌ Greeting error: {str(e)}")
        return jsonify({
            'response': "Hey there! Ready to chat? 🎉",
            'error': str(e)
        })