# Gunicorn configuration file
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5600"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "/app/logs/gunicorn_access.log"
errorlog = "/app/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "piper-tts-api"

# Server mechanics
daemon = False
pidfile = "/app/logs/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if certificates are available)
# keyfile = "/app/ssl/private.key"
# certfile = "/app/ssl/certificate.crt"

# Environment
raw_env = [
    "ENVIRONMENT=production"
]

# Preload app for better performance
preload_app = True

# Worker process lifecycle
def on_starting(server):
    server.log.info("Starting Piper TTS API server")

def on_reload(server):
    server.log.info("Reloading Piper TTS API server")

def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    worker.log.info("Worker received SIGABRT signal")