import os

# auth.py valida estas variables al importarse.
# En tests usamos valores locales y no secretos reales.
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("WORKER_SECRET", "test-worker-secret")
