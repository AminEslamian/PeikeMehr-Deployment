import multiprocessing
import os


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# 3 sync workers is a sensible default for 2 vCPU / 4 GB. Override with
# GUNICORN_WORKERS after measuring the real workload.
workers = env_int(
    "GUNICORN_WORKERS",
    max(2, min(4, multiprocessing.cpu_count())),
)
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")
timeout = env_int("GUNICORN_TIMEOUT", 120)
graceful_timeout = env_int("GUNICORN_GRACEFUL_TIMEOUT", 30)
keepalive = env_int("GUNICORN_KEEPALIVE", 5)
max_requests = env_int("GUNICORN_MAX_REQUESTS", 1000)
max_requests_jitter = env_int("GUNICORN_MAX_REQUESTS_JITTER", 100)

# The backend is only reachable from the Docker network. Trust the proxy
# headers set by the frontend nginx container for logging/client IPs.
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")

accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'
)

if os.path.isdir("/dev/shm") and os.access("/dev/shm", os.W_OK):
    worker_tmp_dir = "/dev/shm"
