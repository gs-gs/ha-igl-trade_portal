"""
Helpers to notarize OA files
"""
import hashlib
import json
import logging
import time

import boto3
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class NotaryService:
    """
    Accepting document body (expected to have OA JSON there) starts the remote notarisation
    process, so this file can be verified later

    In its current state it just puts file to the configured bucket and ensurees that
    remote OA worker is be informed about it (by sending SQS message)

    In the future it could also handle feedback from that service and handle
    possible errors (the OA service is very sensitive to format issues), bulk issues,
    revokations and so on.

    While this class is not covered by unit tests it's not so interesting - the code is simple
    and is constantly tested by manual actions on any installation
    """

    def _get_aws_creds(self, region=None):
        return {
            # having access keys is useful for local development and non-AWS deployment
            # but prod cloud setup usually have it empty so creds are picked from elsewhere
            "aws_access_key_id": (
                settings.OA_AWS_ACCESS_KEYS.split(":")[0] or None if settings.OA_AWS_ACCESS_KEYS else None
            ),
            "aws_secret_access_key": (
                settings.OA_AWS_ACCESS_KEYS.split(":")[1] or None if settings.OA_AWS_ACCESS_KEYS else None
            ),
            "region_name": region,
        }

    def notarize_file(self, document_body: str):
        """
        Accepts file content as string (containing rendered OA JSON, file up to several MB)
        Puts it to the place from which notarisation worker will read it and do its complicated work
        """
        if getattr(settings, "IS_UNITTEST", False) is True:
            raise EnvironmentError("This procedure must not be called from unittest")

        if not settings.OA_UNPROCESSED_BUCKET_NAME:
            logger.warning(
                "Asked to notarize file but the service is not configured well"
            )
            return False

        t0 = time.time()

        s3res = boto3.resource("s3", **self._get_aws_creds()).Bucket(
            settings.OA_UNPROCESSED_BUCKET_NAME
        )

        body = document_body.encode("utf-8")
        doc_key = hashlib.sha1(body).hexdigest().lower()
        content_length = len(body)

        date = str(timezone.now().date())
        key = f"{date}/{doc_key}.json"
        s3res.Object(key).put(Body=body, ContentLength=content_length)

        logger.info("The file %s to be notarized has been uploaded in %ss", key, round(time.time() - t0, 6))
        self._send_manual_notification(key)
        return True

    def _send_manual_notification(self, key: str):
        """
        If the bucket itself doesn't send these notifications for some reason
        We forge it so worker is aware. Another side effect is that we can
        change the notification format, including our custom parameters
        """
        if not settings.OA_UNPROCESSED_QUEUE_URL:
            # it's fine, we don't want to send them
            return True

        if getattr(settings, "IS_UNITTEST", False) is True:
            raise EnvironmentError("This procedure must not be called from unittest")

        unprocessed_queue = boto3.resource(
            "sqs",
            **self._get_aws_creds(region=settings.AWS_REGION)
        ).Queue(
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
        logger.info("Sent notification about file %s to be notarized", key)
        return True
