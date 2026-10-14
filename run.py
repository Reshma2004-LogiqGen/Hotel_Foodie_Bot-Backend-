"""
Food Friend Backend - Main Entry Point
Run this file to start the Flask server on your computer.
On a hosting server use gunicorn instead: gunicorn run:app (settings in gunicorn.conf.py).
"""

import os
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
    print(f"   2. Staff dashboard: https://{local_ip}:5173/admin")
    print()
    print("🔗 API endpoints:")
    print("   - GET  /api/menu?code=<table QR code>")
    print("   - POST /api/orders  (customer places an order)")
    print("   - GET  /api/orders/<order number>?code=<table QR code>")
    print("   - GET  /api/orders/<order number>/nutrition?code=<table QR code>  (OpenAI)")
    print("   - POST /api/chat  (OpenAI, needs the table QR code and order number)")
    print("   - GET  /api/tables/<number>?code=<table QR code>")
    print("   - POST /api/auth/register, /api/auth/login  (admin & chef accounts)")
    print("   - /api/kitchen/orders  (kitchen view, chef or admin login)")
    print("   - /api/admin/...  (admin view, admin login)")
    print()
    print("   Staff login:    https://localhost:5173/admin/login")
    print("   Staff register: https://localhost:5173/admin/register")
    print()
    print("=" * 50)
    
    # Debug mode lets anyone who can open the server run code on it, so it is only on with FLASK_DEBUG=1.
    app.run(debug=os.getenv('FLASK_DEBUG') == '1', host='0.0.0.0', port=int(os.getenv('PORT', '5000')))