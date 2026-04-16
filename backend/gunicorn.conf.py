import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'gthread'
threads = int(os.environ.get('GUNICORN_THREADS', '2'))

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Security
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# Reliability
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sus'
