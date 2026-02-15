"""Gunicorn configuration for production deployment."""

import multiprocessing
import os

bind = "0.0.0.0:8000"
backlog = 2048

workers = int(os.getenv("WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 10000
max_requests_jitter = 1000
timeout = 60
keepalive = 5

accesslog = "/var/log/aws-cost-agent/access.log"
errorlog = "/var/log/aws-cost-agent/error.log"
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

proc_name = "aws-cost-agent"

daemon = False
pidfile = "/var/run/aws-cost-agent/gunicorn.pid"

graceful_timeout = 30
