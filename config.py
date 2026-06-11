import os
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


def env_bool(name, default='false'):
    return os.getenv(name, default).strip().lower() in {'1', 'true', 'yes', 'on'}


def normalize_database_url(database_url):
    """Return a SQLAlchemy-compatible database URL with Neon-friendly SSL."""
    if not database_url:
        return 'sqlite:///' + os.path.join(basedir, 'app.db')

    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    if database_url.startswith('postgresql') and env_bool('DATABASE_SSL_REQUIRE', 'true'):
        parts = urlsplit(database_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.setdefault('sslmode', 'require')
        database_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    return database_url


class BaseConfig:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.getenv('DATABASE_URL'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH') or 4 * 1024 * 1024)

    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME') or 'admin'
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL') or 'admin@example.com'
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

    DEBUG = False
    TESTING = False
    AUTO_CREATE_DATABASE = env_bool('AUTO_CREATE_DATABASE', 'true')
    REQUIRE_PRODUCTION_CONFIG = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE')
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    PREFERRED_URL_SCHEME = 'http'

    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv('SESSION_IDLE_TIMEOUT_MINUTES', '30')))
    SESSION_REFRESH_EACH_REQUEST = True

    RATELIMIT_ENABLED = env_bool('RATELIMIT_ENABLED', 'true')
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT') or '200 per day;50 per hour'
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')
    RATELIMIT_HEADERS_ENABLED = True

    CACHE_TYPE = 'RedisCache' if os.getenv('REDIS_URL') else 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT') or 300)
    CACHE_REDIS_URL = os.getenv('REDIS_URL')

    METRICS_AUTH_TOKEN = os.getenv('METRICS_AUTH_TOKEN', '')
    PASSWORD_MIN_LENGTH = int(os.getenv('PASSWORD_MIN_LENGTH', '12'))

    MAIL_SERVER = os.getenv('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.getenv('MAIL_PORT') or 587)
    MAIL_USE_TLS = env_bool('MAIL_USE_TLS', 'true')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME') or 'your-email@gmail.com'
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD') or 'your-app-password'
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER') or 'noreply@inventory.com'


class DevelopmentConfig(BaseConfig):
    DEBUG = env_bool('FLASK_DEBUG', 'true')


class ProductionConfig(BaseConfig):
    DEBUG = False
    AUTO_CREATE_DATABASE = False
    REQUIRE_PRODUCTION_CONFIG = True
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    WTF_CSRF_ENABLED = True
    PREFERRED_URL_SCHEME = 'https'
    CACHE_TYPE = 'RedisCache' if os.getenv('REDIS_URL') else 'SimpleCache'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
        'pool_size': int(os.getenv('SQLALCHEMY_POOL_SIZE', '10')),
        'max_overflow': int(os.getenv('SQLALCHEMY_MAX_OVERFLOW', '20')),
    }


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    ADMIN_PASSWORD = 'test-admin-password'
    AUTO_CREATE_DATABASE = True


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}


def get_config():
    env_name = os.getenv('FLASK_ENV') or os.getenv('APP_ENV') or os.getenv('RENDER_ENV') or 'development'
    if env_name == 'production':
        return ProductionConfig
    if env_name == 'testing':
        return TestingConfig
    return DevelopmentConfig


# Backwards-compatible alias for existing imports.
Config = DevelopmentConfig
