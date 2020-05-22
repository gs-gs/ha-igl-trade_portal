from . import Env
env = Env()

CACHE_REDIS_URL = env("REDIS_URL", default="redis://redis:6379/1")

if CACHE_REDIS_URL.endswith("/0"):
    # change database from 0 to 1 to avoid collisions with celery broker
    CACHE_REDIS_URL = CACHE_REDIS_URL[:-2] + "/1"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CACHE_REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicing memcache behavior.
            # http://niwinz.github.io/django-redis/latest/#_memcached_exceptions_behavior
            "IGNORE_EXCEPTIONS": True,
        },
    }
}
