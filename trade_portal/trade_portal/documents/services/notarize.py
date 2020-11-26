"""
Things related to the CoO packaging and sending to the upstream
"""
import json
import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class NotaryService:
    """
    Service made solely for files notarisation.
    In it's current state it just puts some file to some bucket and ensurees that
    remote OA worker will be informed about it.

    In the future it could also handle notifiations from that service and handle
    possible errors (the OA service is very sensitive to format issues)
    """

    @classmethod
    def notarize_file(cls, doc_key: str, document_body: str):
        import boto3  # local import because some setups may not even use it

        if not settings.OA_UNPROCESSED_BUCKET_NAME:
            logger.warning(
                "Asked to notarize file but the service is not configured well"
            )
            return False

        s3_config = {
            "aws_access_key_id": (
                settings.OA_AWS_ACCESS_KEYS.split(":")[0] or None if settings.OA_AWS_ACCESS_KEYS else None
            ),
            "aws_secret_access_key": (
                settings.OA_AWS_ACCESS_KEYS.split(":")[1] or None if settings.OA_AWS_ACCESS_KEYS else None
            ),
            "region_name": None,
        }
        s3res = boto3.resource("s3", **s3_config).Bucket(
            settings.OA_UNPROCESSED_BUCKET_NAME
        )

        body = document_body.encode("utf-8")
        content_length = len(body)

        date = str(timezone.now().date())
        key = f"{date}/{doc_key}.json"
        s3res.Object(key).put(Body=body, ContentLength=content_length)
        logger.info("The file %s to be notarized has been uploaded", key)
        cls.send_manual_notification(key)
        return True

    @classmethod
    def send_manual_notification(cls, key: str):
        """
        If the bucket itself doesn't send these notifications for some reason
        We forge it so worker is aware. Another side effect is that we can
        change the notification format, including our custom parameters
        """
        import boto3  # local import because some setups may not even use it

        if not settings.OA_UNPROCESSED_QUEUE_URL:
            # it's fine, we don't want to send them
            return

        s3_config = {
            "aws_access_key_id": (
                settings.OA_AWS_ACCESS_KEYS.split(":")[0] or None if settings.OA_AWS_ACCESS_KEYS else None
            ),
            "aws_secret_access_key": (
                settings.OA_AWS_ACCESS_KEYS.split(":")[1] or None if settings.OA_AWS_ACCESS_KEYS else None
            ),
            "region_name": "ap-southeast-2",
        }

        unprocessed_queue = boto3.resource("sqs", **s3_config).Queue(
            settings.OA_UNPROCESSED_QUEUE_URL
        )
        unprocessed_queue.send_message(
            MessageBody=json.dumps(
                {
                    "Records": [
                        {
                            "s3": {
                                "bucket": {"name": settings.OA_UNPROCESSED_BUCKET_NAME},
                                "object": {"key": key},
                            }
                        }
                    ]
                }
            )
        )
        logger.info("The notification about file %s to be notarized has been sent", key)
        return
