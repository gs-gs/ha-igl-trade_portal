import base64
import json
import logging

import requests

from django.conf import settings

logger = logging.getLogger(__name__)


class OaVerificationError(Exception):
    pass


class OaVerificationService:
    """
    Object containing the code to verify OA documents
    As QR codes, binary files and so on.
    """

    def wrap_file(self, unwrapped_json):
        raise NotImplementedError()

    def verify_file(self, file_content):
        """
        Helper function which verifies the OA body and returns dict with some
        useful variables set

        The file_content parameter must be cleartext bytes
        (already decrypted but not unwrapped)

        Has next keys:
        * status - valid/invalid/error
        * verify_result - list of dicts about specific verification details
        * verify_result_rotated - the same but in a format comfortable for display
        * unwrapped_file - bytes with unwrapped file content (the JSON to display or render)
        * oa_raw_data - dict made by parsing the unwrapped file
        * oa_bas64 - base64 representation of the wrapped file for easy "download" actions
        * template_url - URL of the renderer to use in iframe which renders the document
        * attachments - list of binary (or text) attached files like PDFs
        """
        result = {}

        try:
            json_content = json.loads(file_content)
        except (ValueError, TypeError):
            result = {
                "status": "error",
                "error_message": "The provided file is not a valid JSON thus not OA document",
            }
            return result
        else:
            # try to find the local document referring that file
            doc_number = json_content.get("data", {}).get("certificateOfOrigin", {}).get("id", "")
            if doc_number.count(":") >= 2:
                # might be wrapped document number
                doc_number = doc_number.split(":", maxsplit=2)[2]

        try:
            api_verify_resp = self._api_verify_file(file_content)
        except OaVerificationError as e:
            result = {
                "status": "error",
                "error_message": str(e),
            }
        else:
            # the file has been verified and either valid or invalid, calculate the final status
            result["status"] = "valid"
            result["verify_result"] = api_verify_resp.copy()
            result["verify_result_rotated"] = {}

            valid_subjects_count = 0

            for row in api_verify_resp:
                if row["status"].lower() not in ("valid", "skipped"):
                    result["status"] = "invalid"
                if row["status"].lower() == "valid":
                    valid_subjects_count += 1
                result["verify_result_rotated"][row.get("name")] = row

            if valid_subjects_count < 2 and result["status"] == "valid":
                # although we didn't find any invalid/error subjects
                # there weren't enough valid ones, so most of them are skipped probably
                result["status"] = "error"
                result["error_message"] = (
                    "The document doesn't have at least 2 valid subjects. "
                    "Most likely it's just not an OA document"
                )
        if result["status"] == "valid":
            # worth further parsing only if the file is valid
            try:
                result["unwrapped_file"] = self._unwrap_file(file_content)
                result["oa_raw_data"] = json.loads(file_content)
                result["oa_base64"] = base64.b64encode(file_content).decode("utf-8")
            except Exception as e:
                logger.exception(e)
                # or likely our code has some bug or unsupported format in it
                raise OaVerificationError(
                    "Unable to unwrap the OA file - it's structure may be invalid"
                )
            else:
                result["template_url"] = requests.get(
                    result["unwrapped_file"]
                    .get("data", {})
                    .get("$template", {})
                    .get("url")
                ).url
                if result["template_url"] and not result["template_url"].startswith("http"):
                    result["template_url"] = "https://" + result["template_url"]
                result["attachments"] = self._parse_attachments(
                    result["unwrapped_file"].get("data", {})
                )
        result["doc_number"] = doc_number
        logger.info(result)
        return result

    def _api_verify_file(self, file_content):
        try:
            resp = requests.post(
                settings.OA_VERIFY_API_URL,
                files={
                    "file": file_content,
                },
            )
        except Exception as e:
            raise OaVerificationError(
                f"Verifier temporary unavailable (error {e.__class__.__name__}); please try again later"
            )
        if resp.status_code == 200:
            # now it contains list of dicts, each tells us something
            # about one aspect of the OA document
            return resp.json()
        elif resp.status_code == 400:
            logger.warning("OA verify: %s %s", resp.status_code, resp.json())
            message = resp.json().get("error") or "unknown error"
            raise OaVerificationError(f"Verifier doesn't accept that file: {message}")
        else:
            logger.warning(
                "%s resp from the OA Verify endpoint - %s",
                resp.status_code,
                resp.content,
            )
            raise OaVerificationError(
                f"Verifier temporary unavailable (error {resp.status_code}); please try again later"
            )

    def _unwrap_file(self, content):
        """
        Warning: it's less reliable but quick
        It's better to cal OA.unwrap() method
        """

        def unwrap_it(what):
            if isinstance(what, str):
                # wrapped something
                if what.count(":") >= 2:
                    uuidvalue, vtype, val = what.split(":", maxsplit=2)
                    if len(uuidvalue) == len("6cdb27f1-a46e-4dea-b1af-3b3faf7d983d"):
                        if vtype == "string":
                            return str(val)
                        elif vtype == "boolean":
                            return True if val.lower() == "true" else False
                        elif vtype == "number":
                            return int(val)
                        elif vtype == "null":
                            return None
                        elif vtype == "undefined":
                            return None
                    else:
                        return what
            elif isinstance(what, list):
                return [unwrap_it(x) for x in what]
            elif isinstance(what, dict):
                return {k: unwrap_it(v) for k, v in what.items()}
            else:
                return what

        wrapped = json.loads(content)
        return unwrap_it(wrapped)

    def _parse_attachments(self, data):
        """
        This procedure is needed because different document formats have
        their attachments in different places
        """
        attachments = data.get("attachments") or []
        # is it UN CoO?
        unCoOattachedFile = data.get("certificateOfOrigin", {}).get("attachedFile")
        if unCoOattachedFile:
            # format of each dict: file, encodingCode, mimeCode
            attachments.append(
                {
                    "type": unCoOattachedFile["mimeCode"],
                    "filename": "file."
                    + unCoOattachedFile["mimeCode"].rsplit("/")[-1].lower(),
                    "data": unCoOattachedFile["file"],
                }
            )
        return attachments
