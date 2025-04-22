"""
Gunicorn configuration for production deployment
"""

# Gunicorn configuration settings
bind = "0.0.0.0:8000"
workers = 4  # Recommended: 2 * number_of_cores + 1
worker_class = "gevent"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

# Logging settings
errorlog = "logs/error.log"
accesslog = "logs/access.log"
loglevel = "info"

# Process naming
proc_name = "ticket_system"
