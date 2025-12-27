"""
Food Friend Backend - Helper Utilities
Common utility functions used across the application
"""

import re
import json
from datetime import datetime


def clean_json_response(text: str) -> str:
    """
    Clean up a JSON response that might have markdown formatting
    
    Args:
        text: Raw text that might contain JSON with markdown
        
    Returns:
        Cleaned JSON string
    """
    # Remove markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines if they're markdown markers
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    
    # Remove "json" prefix if present
    if text.strip().startswith("json"):
        text = text.strip()[4:]
    
    return text.strip()


def parse_json_safely(text: str) -> dict:
    """
    Safely parse JSON from text, handling common issues
    
    Args:
        text: Text that should contain JSON
        
    Returns:
        Parsed dictionary or None if parsing fails
    """
    try:
        cleaned = clean_json_response(text)
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return None


def format_currency(amount: float) -> str:
    """Format a number as currency"""
    return f"${amount:.2f}"


def format_timestamp(dt: datetime = None) -> str:
    """Format a datetime as ISO string"""
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def validate_persona(persona: str) -> bool:
    """Check if a persona is valid"""
    valid_personas = [
        'friend', 'lover', 'business_partner', 'stranger',
        'celebrity', 'therapist', 'drunk_uncle'
    ]
    return persona in valid_personas


def validate_gender(gender: str) -> bool:
    """Check if gender is valid"""
    return gender in ['male', 'female', 'other']


def validate_relationship_status(status: str) -> bool:
    """Check if relationship status is valid"""
    return status in ['single', 'committed', 'married', 'couple']


def sanitize_message(message: str) -> str:
    """Sanitize user message for safety"""
    # Remove any potential HTML/script tags
    message = re.sub(r'<[^>]+>', '', message)
    # Limit length
    return message[:1000]
