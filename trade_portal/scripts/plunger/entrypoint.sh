#!/bin/bash
set -o errexit
set -o nounset

# Decrypt Base64 encoded string encrypted using AWS KMS CMK keys
AWS_REGION="${AWS_REGION:-""}"
KMS_PREFIX="${KMS_PREFIX:-"kms+base64:"}"

if [[ -n "${AWS_REGION}" ]]; then
    for ENV_VAR in $( printenv ); do
        KEY="$( echo "${ENV_VAR}" | cut -d'=' -f1)"
        VALUE="$( echo "${ENV_VAR}" | cut -d'=' -f2-)"

        if [[ $VALUE == "${KMS_PREFIX}"* ]]; then
            echo "AWS KMS - Decrypting Key ${KEY}..."
            CIPHER_BLOB_PATH="/tmp/ENV-${KEY}-cipher.blob"
            echo ${VALUE#"${KMS_PREFIX}"} | base64 -d > "${CIPHER_BLOB_PATH}"
            VALUE="$(aws --region "${AWS_REGION}" kms decrypt --ciphertext-blob "fileb://${CIPHER_BLOB_PATH}" --output text --query Plaintext | base64 -d || exit $?)"
            export "${KEY}"="${VALUE}"
        fi
    done
fi

exec "$@"
