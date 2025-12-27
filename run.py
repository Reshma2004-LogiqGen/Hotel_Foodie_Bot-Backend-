"""
Food Friend Backend - Main Entry Point
Run this file to start the Flask server
"""

import socket
from app import create_app

app = create_app()


def get_local_ip():
    """Get the local network IP address"""
    try:
        # Connect to external server to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Unable to determine"


if __name__ == '__main__':
    local_ip = get_local_ip()
    
    print("=" * 50)
    print("🍕 Food Friend Backend Starting...")
    print("=" * 50)
    print()
    print("📡 Server URLs:")
    print(f"   Local:   http://localhost:5000")
    print(f"   Network: http://{local_ip}:5000")
    print()
    print("📱 For MOBILE ACCESS:")
    print(f"   1. Frontend: https://{local_ip}:5173")
    print(f"      (Accept the security warning for self-signed cert)")
    print(f"   2. Chef Portal: https://{local_ip}:5173/chef")
    print()
    print("🔗 API endpoints:")
    print("   - POST /api/chat")
    print("   - POST /api/nutrition/generate")
    print("   - POST /api/order")
    print("   - GET  /api/orders")
    print("   - PUT  /api/order/<id>/status")
    print()
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)