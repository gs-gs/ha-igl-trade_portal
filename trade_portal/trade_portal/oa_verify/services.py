import base64
import json
import logging
import time
import urllib
from io import BytesIO

import PyPDF2
import requests
from django.conf import settings
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode

from trade_portal.documents.services.encryption import AESCipher

logger = logging.getLogger(__name__)


class OaVerificationError(Exception):
    pass


class OaVerificationService:
    """
    Object containing the code to verify JSON OA TT documents
    """

    def verify_json_tt_document(self, file_content):
        """
        Return verification result dict
        Accepting OA file body as cleartext bytes (already decrypted but not unwrapped)

        Any other business-facing verification method (PDF upload, QR Code reading) ends
        in some TT document verification anyway

        The result has next keys:
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

        self.kick_verify_api()

        t0 = time.time()
        try:
            api_verify_resp = self._api_verify_tt_json_file(file_content)
        except OaVerificationError as e:
            logger.info("Document verification (api call), failed in %ss", round(time.time() - t0, 4))
            result = {
                "status": "error",
                "error_message": str(e),
            }
        else:
            logger.info("Document verification (api call), success in %ss", round(time.time() - t0, 4))
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
                result["template_url"] = self._retrieve_template_url(result["unwrapped_file"])
                result["attachments"] = self._parse_attachments(
                    result["unwrapped_file"].get("data", {})
                )
        result["doc_number"] = doc_number

        # fill issued_by
        try:
            result["issued_by"] = result["verify_result_rotated"].get(
                "OpenAttestationDnsTxt", {}
            ).get("data", [{}])[0].get("location")
        except Exception as e:
            logger.exception(e)
            result["issued_by"] = None

        if not result["issued_by"]:
            try:
                # try DID
                vrr = result["verify_result_rotated"].get("OpenAttestationDnsDidIdentityProof", {}).get("data")
                if isinstance(vrr, list):
                    for row in vrr:
                        result["issued_by"] = row.get("location")
                        if result["issued_by"]:
                            break
                elif isinstance(vrr, dict):
                    result["issued_by"] = vrr.get("location")
            except Exception as e:
                logger.exception(e)

        if not result["issued_by"]:
            try:
                # try TXT
                vrr = result["verify_result_rotated"].get("OpenAttestationDnsTxtIdentityProof", {}).get("data")
                if isinstance(vrr, list):
                    for row in vrr:
                        result["issued_by"] = row.get("location")
                        if result["issued_by"]:
                            break
                elif isinstance(vrr, dict):
                    result["issued_by"] = vrr.get("location")
            except Exception as e:
                logger.exception(e)
        return result

    def verify_pdf_file(self, pdf_file):
        """
        Accepting uploaded file as object with `.read()` method
        Tries to parse that PDF file and retrieve a valid QR code from it
        And verify that QR code
        https://github.com/gs-gs/ha-igl-project/issues/54
        """
        try:
            valid_qrcodes = PdfVerificationService(pdf_file).get_valid_qrcodes()
        except Exception as e:
            if "file has not been decrypted" in str(e):
                return {
                    "status": "error",
                    "error_message": (
                        "Verification of encrypted PDF files directly is not supported; "
                        "please use QR code reader and your camera."
                    ),
                }
            else:
                logger.exception(e)
                return {
                    "status": "error",
                    "error_message": (
                        "Unable to parse the PDF file"
                    ),
                }
        if not valid_qrcodes:
            return {
                "status": "error",
                "error_message": (
                    "No QR codes were found in the PDF file; "
                    "Please try to use 'Read QR code using camera' directly"
                ),
            }
        elif len(valid_qrcodes) > 1:
            return {
                "status": "error",
                "error_message": (
                    "There are multiple valid QR codes in that document; "
                    "please scan the desired one manually"
                ),
            }
        return self.verify_qr_code(code=valid_qrcodes[0])

    def verify_qr_code(self, code: str = None, query: dict = None):
        """
        Return QR code verification result or error

        Next kinds of QR codes are supported:
        1. New self-contained format
            https://action.openattestation.com/?q={q}
            where q is urlencoded JSON something like
            {
                "type": "DOCUMENT",
                "payload": {
                    "uri": "https://trade.c1.devnet.trustbridge.io/oa/1d490b1b-aee8-47f3-bfa5-d08c67e940eb/",
                    "key": "DC97D0BA857D6FC213959F6F42E77AF0426C8329ABF3855B5000FED82B86E82C",
                    "permittedActions": ["VIEW"],
                    "redirect": "https://dev.tradetrust.io"
                }
            }

        2. Old tradetrust data as json
            tradetrust://{"uri":"https://trade.c1.devnet.trustbridge.io/oa/1d490b1b-aee8-47f3-bfa5-d08c67e940eb/#DC97D0BA857D6FC213959F6F42E77AF0426C8329ABF3855B5000FED82B86E82C"}

        Exceptions are raised but not catched here, the calling code should do it
        """
        if code:
            # has been already read and parsed
            if code.startswith("https://") or code.startswith("http://"):
                # new approach
                components = urllib.parse.urlparse(code)
                params = urllib.parse.parse_qs(components.query)
                req = json.loads(params["q"][0])
                if req["type"].upper() == "DOCUMENT":
                    uri = req["payload"]["uri"]
                    key = req["payload"]["key"]  # it's always AES key
            elif code.startswith("tradetrust://"):
                # old approach
                json_body = code.split("://", maxsplit=1)[1]
                params = json.loads(json_body)["uri"]
                uri, key = params.rsplit("#", maxsplit=1)
            else:
                raise OaVerificationError("Unsupported QR code format")
        elif query:
            # the url has been navigated, so we already have both uri and key
            uri, key = query["uri"], query["key"]

        # this will contain fields cipherText, iv, tag, type
        logger.info("Retrieving document %s using key ending with %s", uri, str(key)[-5:])

        try:
            document_info = requests.get(uri).json()["document"]
        except Exception as e:
            logger.exception(e)
            raise OaVerificationError(
                "Unable to download the OA document from given url (this usually "
                "means that remote service is down or acting incorrectly"
            )

        cp = AESCipher(key)
        cleartext_b64 = cp.decrypt(
            document_info["iv"],
            document_info["tag"],
            document_info["cipherText"],
        ).decode("utf-8")
        cleartext = base64.b64decode(cleartext_b64)

        logger.info("Unpacking document %s", uri)

        return OaVerificationService().verify_json_tt_document(cleartext)

    def kick_verify_api(self):
        """
        Call the healthcheck API to ensure it's warm and ready
        """
        if not settings.OA_VERIFY_API_HEALTHCHECK_URL:
            return False
        t0 = time.time()
        try:
            kick_resp = requests.get(settings.OA_VERIFY_API_HEALTHCHECK_URL)
        except Exception as e:
            logger.error(
                "Verifier healthcheck temporary unavailable (%s)", str(e)
            )
            return False
        else:
            if kick_resp.status_code != 200:
                logger.warning(
                    "OA Verify API healthcheck resp %s, %s",
                    kick_resp.status_code,
                    kick_resp.content
                )

        kick_timeout = time.time() - t0
        logger.info(
            "Verifier healthcheck resp is %s, %ss",
            kick_resp.status_code,
            round(kick_timeout, 4)
        )
        return kick_resp.status_code == 200

    def _api_verify_tt_json_file(self, file_content):
        """
        Return response from the remote OA verification API
        Accepting TT JSON file content as bytes string

        Raises OaVerificationError with details if it's impossible
        Or returns raw verify endpoint response as dict if success
        """
        try:
            resp = requests.post(
                settings.OA_VERIFY_API_URL,
                files={
                    "file": file_content,
                },
            )
        except Exception as e:
            raise OaVerificationError(
                f"Verifier is temporary unavailable (reported {e.__class__.__name__}); "
                f"please try again later. We are already aware of that issue and working on it."
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
                f"Verifier is temporary unavailable (reported {resp.status_code}); please try again later."
                f"We are already aware of that issue and working on it."
            )

    def _unwrap_file(self, content):
        """
        This is a reproduction of OA.unwrap() method and will stop working if
        OA wrapping rules change in the future
        But it's quick and written in Python, not JS
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
                else:
                    # could be unwrapped already
                    # (which means the document is invalid)
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

    def _retrieve_template_url(self, unwrapped_file):
        """
        Return resolved template url (following all requests)
        Or just the OA-coded value if can't perform request with 200 resp
        """
        # v2 url format
        url = unwrapped_file.get("data", {}).get("$template", {}).get("url")
        if not url:
            url = unwrapped_file.get("openAttestationMetadata", {}).get("template", {}).get("url")
        if not url:
            logger.warning("Unable to fetch renderer URL from OA file")
            return ""

        try:
            url_resp = requests.get(url)
        except Exception as e:
            logger.exception(e)
            ret = url
        else:
            if url_resp.status_code == 200:
                ret = url_resp.url
            else:
                ret = url
            if ret and not ret.startswith("http"):
                ret = "https://" + ret
        return ret


class PdfVerificationService:
    """
    Service to extract supported QR codes from provided PDF
    Never updates the input, only reads and parses it

    https://github.com/gs-gs/ha-igl-project/issues/54
    """

    def __init__(self, pdf_file: bytes):
        self._pdf_binary = pdf_file

    def get_valid_qrcodes(self):
        """
        For the PDF with which this service has been initialized
        Tries to parse it
        Retrieving all images and parsing them as QR codes
        And if parsed - verify QR code format to be one of supported ones
        And return the text from all the supported QR codes

        Seems to handle scanned PDFs well, but real usage will give us a lot of complex PDFs which
        are not supported - so just need to be considered as well
        """
        qr_texts_found = set()

        try:
            reader = PyPDF2.PdfFileReader(self._pdf_binary)
            pages_count = reader.numPages
        except Exception as e:
            logger.exception(e)
            # try another library to rasterize that PDF and read QRs from images
            qr_texts_found = self._try_rasterisation()
        else:
            # PDF can be parsed, do it
            if pages_count > 20:
                pages_count = 20  # performance
            for page_num in range(0, pages_count):
                page = reader.getPage(page_num)

                if '/XObject' in page['/Resources']:
                    xObject = page['/Resources']['/XObject'].getObject()
                    qr_texts_found = qr_texts_found.union(self._parse_xobject(xObject))
                else:
                    # nothing to parse - no xobjects
                    pass
            if not qr_texts_found:
                # try rasterisation in that case as well
                qr_texts_found = self._try_rasterisation()

        # now qr_texts_found contains all texts of any format from the first page of that PDF
        # first - we filter out all which are not supported
        supported_qr_codes = []
        for qr_code in qr_texts_found:
            if self.is_qr_of_supported_format(qr_code):
                supported_qr_codes.append(qr_code)
        return supported_qr_codes or None

    def _parse_xobject(self, xObject):
        """
        For given xObject
        Tries to parse it as Image or, in case of Form, parses it recursively
        """
        qrtexts_in_that_xobject = set()
        for obj in xObject:
            try:
                if xObject[obj]['/Subtype'] == '/Form':
                    if '/XObject' in xObject[obj]['/Resources']:
                        qrtexts_in_that_xobject = qrtexts_in_that_xobject.union(
                            self._parse_xobject(xObject[obj]['/Resources']['/XObject'].getObject())
                        )
                elif xObject[obj]['/Subtype'] == '/Image':
                    size = (xObject[obj]['/Width'], xObject[obj]['/Height'])
                    data = xObject[obj].getData()  # already unfiltered
                    if xObject[obj]['/ColorSpace'] == '/DeviceRGB':
                        mode = "RGB"
                    else:
                        mode = "P"

                    if '/Filter' in xObject[obj]:
                        filters = xObject[obj]['/Filter']

                        # we are interested only in last filter because PyPDF2 does all unpacking for us
                        if isinstance(filters, list):
                            the_filter = filters[-1]
                        else:
                            the_filter = filters

                        # now we parse the image, assuming all filters were unfiltered
                        if the_filter == '/FlateDecode':
                            img = Image.frombytes(mode, size, data)
                        elif the_filter == '/DCTDecode':
                            # data is already JPEG
                            img = Image.open(BytesIO(data))
                        elif the_filter == '/JPXDecode':
                            # data is already jp2 format
                            img = Image.open(BytesIO(data))
                        elif the_filter == '/CCITTFaxDecode':
                            # data is already tiff format
                            img = Image.open(BytesIO(data))
                        else:
                            # unsupported something, ignore that file
                            logger.warning("Unsupported PDF image filter %s", the_filter)
                            img = None
                    else:
                        img = Image.frombytes(mode, size, data)

                    if img:
                        qr_texts_in_this_image = self.parse_qr_code(img)
                        if qr_texts_in_this_image:
                            qrtexts_in_that_xobject = qrtexts_in_that_xobject.union(qr_texts_in_this_image)
            except Exception as e:
                # some parsing issue, just skip to the next xObject
                # we won't read images from that block but at least there is a chance that we don't need it anyway
                logger.exception(e)
        return qrtexts_in_that_xobject

    def parse_qr_code(self, img: Image):
        decoded_texts = set()
        for decoded in pyzbar_decode(img):
            if decoded.type == "QRCODE":
                decoded_texts.add(decoded.data.decode("utf-8"))
        return decoded_texts or None

    def is_qr_of_supported_format(self, text: str) -> bool:
        if text.startswith("tradetrust://{") and text.endswith("}"):
            json_body = text[len("tradetrust://"):]
            try:
                json.loads(json_body)
            except Exception:
                pass
            else:
                return True  # tradetrust format, JSON with prefix
        if text.startswith("http://") or text.startswith("https://"):
            # possibly a link format
            try:
                components = urllib.parse.urlparse(text)
                params = urllib.parse.parse_qs(components.query)
                req = json.loads(params["q"][0])
                if req["type"].upper() == "DOCUMENT":
                    req["payload"]["uri"]
                    req["payload"]["key"]  # it's always AES
                else:
                    raise KeyError("Not a DOCUMENT type")
            except KeyError:
                pass  # not our case
            else:
                return True  # http format
        return False

    def _try_rasterisation(self):
        """
        Convert all pages to images and feeds them to QR code finder
        This is used as last resort when usual PDF parsing wasn't able to find any codes
        """
        from pdf2image import convert_from_bytes
        qrcodes = set()
        self._pdf_binary.seek(0)
        images = convert_from_bytes(self._pdf_binary.read())
        for image in images:
            this_page_codes = self.parse_qr_code(image)
            if this_page_codes:
                qrcodes = qrcodes.union(this_page_codes)
        return qrcodes
