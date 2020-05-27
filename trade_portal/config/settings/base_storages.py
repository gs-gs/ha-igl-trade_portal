from . import Env
env = Env()
# We always pretend to use S3: Minio locallly and AWS S3 on prod
# other storages may be added when we know about them

AWS_ACCESS_KEY_ID = env("DJANGO_AWS_ACCESS_KEY_ID", default=None) or None
AWS_SECRET_ACCESS_KEY = env("DJANGO_AWS_SECRET_ACCESS_KEY", default=None) or None

AWS_STORAGE_BUCKET_NAME = env("DJANGO_AWS_STORAGE_BUCKET_NAME", default=None)  # "storage"

AWS_S3_ENDPOINT_URL = env(
    "S3_ENDPOINT_URL",
    default=None
) or None

AWS_QUERYSTRING_AUTH = False
_AWS_EXPIRY = 60 * 60 * 24 * 7
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": f"max-age={_AWS_EXPIRY}, s-maxage={_AWS_EXPIRY}, must-revalidate"
}

AWS_DEFAULT_ACL = None
AWS_S3_REGION_NAME = env("DJANGO_AWS_S3_REGION_NAME", default=None)

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
