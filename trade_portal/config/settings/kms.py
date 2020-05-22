import os
import base64
import logging

import boto3

BASE64_PREFIX = 'base64:'
AWS_REGION = os.environ.get('AWS_REGION', None)


def decrypt_kms_data(encrypted_data):
    """Decrypt KMS encoded data."""
    if not AWS_REGION:
        return

    kms = boto3.client('kms', region_name=AWS_REGION)

    decrypted = kms.decrypt(CiphertextBlob=encrypted_data)

    if decrypted.get('KeyId'):
        # Decryption succeed
        decrypted_value = decrypted.get('Plaintext', '')
        if isinstance(decrypted_value, bytes):
            decrypted_value = decrypted_value.decode('utf-8')
        return decrypted_value


def string_or_b64kms(value):
    """Check if value is base64 encoded - if yes, decode it using KMS."""
    if not value:
        return value

    try:
        # Check if environment value base64 encoded
        if isinstance(value, (str, bytes)) and value.startswith(BASE64_PREFIX):
            value = value[len(BASE64_PREFIX):]
            # If yes, decode it using AWS KMS
            data = base64.b64decode(value)
            decrypted_value = decrypt_kms_data(data)

            # If decryption succeed, use it
            if decrypted_value:
                value = decrypted_value
    except Exception as e:
        logging.exception(e)
    return value
