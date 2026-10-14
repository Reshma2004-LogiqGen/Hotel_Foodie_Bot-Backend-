"""
Food Friend Backend - Production server settings
Start the hosted backend with:  gunicorn run:app
"""

import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Exactly one process: the one-order-per-table lock, chat limits and login limits live in memory.
# Threads still let it serve many phones at the same time.
workers = 1
threads = int(os.getenv('GUNICORN_THREADS', '8'))

# A chat reply can wait up to 30 s for OpenAI and is retried, so allow slow requests.
timeout = 120

accesslog = '-'
errorlog = '-'
