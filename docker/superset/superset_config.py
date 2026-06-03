import os

# Security
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "playground_superset_secret")
WTF_CSRF_ENABLED = True

# Database
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SQLALCHEMY_DATABASE_URI",
    "postgresql+psycopg2://playground:playground@postgres:5432/superset"
)

# Cache
CACHE_CONFIG = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
}

# Feature flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
}

# Allow embedding
TALISMAN_ENABLED = False
WTF_CSRF_EXEMPT_LIST = ["superset.views.core.log"]
