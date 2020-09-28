"""
Services related to incoming messages - parsing them and saving to the DB
"""
import base64
import json
import logging
import uuid

import dateutil.parser
import requests
from constance import config
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from trade_portal.documents.models import (
    FTA, Party, Document, DocumentHistoryItem,
    DocumentFile,
)
from trade_portal.documents.services import BaseIgService
from trade_portal.edi3.utils import party_from_json

logger = logging.getLogger(__name__)


class IncomingDocumentProcessingError(Exception):
    def __init__(self, *args, **kwargs):
        self.is_retryable = kwargs.pop("is_retryable", False)
        super().__init__(*args, **kwargs)


class IncomingDocumentService(BaseIgService):

    def process_new(self, doc: Document):
        DocumentHistoryItem.objects.create(
            type="text", document=doc,
            message="Started the incoming document retrieval..."
        )
        # 1. Download the obj from the document API
        try:
            binary_obj_content = self.ig_client.retrieve_document(
                doc.intergov_details["obj"],
            )
        except Exception as e:
            raise IncomingDocumentProcessingError(str(e), is_retryable=True)
        # 2. Save the object somewhere (it could be binary or text file)
        # do we have it already?
        try:
            the_file = DocumentFile.objects.filter(
                doc=doc,
                filename=doc.intergov_details["obj"]
            ).first()
            if the_file:
                logger.info("We already have that file, funny")
            else:
                the_file = DocumentFile.objects.create(
                    doc=doc,
                    filename=doc.intergov_details["obj"],
                    size=len(binary_obj_content),
                )

            path = default_storage.save(
                f'incoming/{doc.id}/{doc.intergov_details["obj"]}.json',
                ContentFile(binary_obj_content)
            )
            # TODO: kill the old file before?
            the_file.file = path
            the_file.save()
        except Exception as e:
            DocumentHistoryItem.objects.create(
                type="error", document=doc,
                message="Failed to store obj from the message",
                object_body=str(e),
            )
            doc.status = Document.STATUS_FAILED
            doc.save()
            return False

        DocumentHistoryItem.objects.create(
            type="docfile", document=doc,
            message="Downloaded the obj from the root message",
            object_body=the_file.filename,
            linked_obj_id=the_file.pk
        )
        # we have saved the obj file, now we are able to parse it
        try:
            self.get_incoming_document_format(doc, binary_obj_content)
        except Exception as e:
            logger.exception(e)
            self._complain_and_die(
                doc,
                "Unable to render the object attached to this message",
            )
        return True

    def get_incoming_document_format(self, doc: Document, binary_obj_content):
        try:
            json_content = json.loads(binary_obj_content)
        except Exception:
            json_content = None

        if json_content:
            logger.info("Found some JSON obj for incoming document %s", doc)
        else:
            return self._complain_and_die(
                doc,
                "Incoming document has no supported obj (can't parse it)"
            )
            return False

        if not isinstance(json_content, dict):
            return self._complain_and_die(
                doc,
                "While incoming document %s obj is json - it's still unsupported",
                doc
            )
            return False

        oa_version = json_content.get("version")
        supported_versions = (
            "https://schema.openattestation.com/2.0/schema.json",
            "https://schema.openattestation.com/3.0/schema.json"
        )

        if oa_version not in supported_versions:
            return self._complain_and_die(
                doc,
                "Incoming document %s obj format '%s' is not supported",
                doc, oa_version
            )

        # wow, it's even OA document
        DocumentHistoryItem.objects.create(
            type="message", document=doc,
            message="Found OA document",
            object_body=oa_version
        )

        try:
            unwrapped_oa = requests.post(
                config.OA_WRAP_API_URL + "/document/unwrap",
                json={
                    "document": json_content,
                    "params": {
                        "version": oa_version,
                    }
                }
            ).json()
        except Exception as e:
            logger.exception(e)
            return self._complain_and_die(
                doc,
                "Can't unwrap %s document for %s",
                oa_version, doc,
            )

        if oa_version == "https://schema.openattestation.com/2.0/schema.json":
            self._process_oa2_document(doc, unwrapped_oa)
        elif oa_version == "https://schema.openattestation.com/3.0/schema.json":
            self._process_oa3_document(doc, unwrapped_oa)
        else:
            return self._complain_and_die(
                doc,
                "Unknown OA version",
                oa_version, doc,
            )
        return True

    def _process_oa2_document(self, doc: Document, data: dict):
        # format of each dict: type, filename, data
        if "certificateOfOrigin" in data:
            # this is a new UN format
            logger.info("Processing UN document format %s", doc)
            coo = data.get("certificateOfOrigin")
            self._parse_un_coo(doc, coo)
        else:
            # some old format
            # TODO: drop it because nobody generates it anymore
            # and think about more robust format support
            logger.info("Processing old document format %s", doc)
            self._parse_old_format(doc, data)
        doc.intergov_details["oa_doc"] = data
        doc.save()
        return

    def _parse_un_coo(self, doc, coo):
        doc.document_number = coo.get("id")
        doc.raw_certificate_data["certificateOfOrigin"] = coo

        # the attachment
        unCoOattachedFile = coo.get("attachedFile")
        if unCoOattachedFile:
            file_mimecode = unCoOattachedFile["mimeCode"]
            file_ext = file_mimecode.rsplit('/')[-1].lower()
            bin_file = base64.b64decode(unCoOattachedFile["file"].encode("utf-8"))
            af = DocumentFile.objects.create(
                doc=doc,
                filename=f"file.{file_ext}" if file_ext else "unknown.bin",
                size=len(bin_file),
                is_watermarked=None,
            )
            path = default_storage.save(
                f'incoming/{doc.id}/attach-{str(uuid.uuid4())}',
                ContentFile(bin_file)
            )
            af.file = path
            af.save()

        # parse FTA and other things
        try:
            issueDateTime = coo.get("issueDateTime")
            if issueDateTime:
                issueDateTime = dateutil.parser.isoparse(issueDateTime)
                if issueDateTime:
                    doc.extra_data["issued_at"] = issueDateTime.isoformat()
        except Exception as e:
            logger.exception(e)

        try:
            if coo.get("isPreferential") is True:
                doc.type = Document.TYPE_PREF_COO
            if coo.get("isPreferential") is False:
                doc.type = Document.TYPE_NONPREF_COO
        except Exception as e:
            logger.exception(e)

        try:
            issuer_data = coo.get("issuer", {})
            doc.issuer = party_from_json(issuer_data)
        except Exception as e:
            logger.exception(e)
            logger.warning(
                "Can't parse issuer for %s", doc
            )

        supplyChainConsignment = coo.get("supplyChainConsignment", {})
        consignor = supplyChainConsignment.get("consignor", {})
        importer = supplyChainConsignment.get("consignee", {})

        doc.consignment_ref_doc_number = supplyChainConsignment.get("id") or ""

        if consignor:
            try:
                doc.exporter = party_from_json(consignor)
                if importer:
                    importer_parts = [
                        importer.get("name"),
                        importer.get("id"),
                    ]
                    doc.importer_name = ' '.join(
                        (x for x in importer_parts if x)
                    )
            except Exception as e:
                logger.exception(e)
                logger.warning("Can't parse consignor or consignee for %s", doc)

        try:
            freeTradeAgreement = coo.get("freeTradeAgreement")
            if freeTradeAgreement:
                try:
                    doc.fta = FTA.objects.get(name=freeTradeAgreement)
                except Exception:
                    logger.warning(
                        "The FTA %s is passed in the inbound document but can't be found locally",
                        freeTradeAgreement
                    )
        except Exception as e:
            logger.exception(e)
        return

    def _parse_old_format(self, doc, data):
        doc.document_number = data.get("id")

        # parse attachments
        for attach in data.pop("attachments", []) or []:
            bin_file = base64.b64decode(attach["data"].encode("utf-8"))
            af = DocumentFile.objects.create(
                doc=doc,
                filename=attach.get("filename") or "unknown.bin",
                size=len(bin_file)
            )
            path = default_storage.save(
                f'incoming/{doc.id}/attach-{str(uuid.uuid4())}',
                ContentFile(bin_file)
            )
            af.file = path
            af.save()

        # parse metadata
        try:
            # these actions are dangerous in terms of exceptions,
            # so we use catchall to handle them one by one if they occure

            issueDateTime = data.get("issueDateTime")
            if issueDateTime:
                issueDateTime = dateutil.parser.isoparse(issueDateTime)
                if issueDateTime:
                    doc.created_at = issueDateTime

            if (data.get("name") or "").lower().endswith("Certificate of Origin".lower()):
                # Certificate of Origin
                if data.get("isPreferential") is True:
                    doc.type = Document.TYPE_PREF_COO
                if data.get("isPreferential") is False:
                    doc.type = Document.TYPE_NONPREF_COO
            supplyChainConsignment = data.get("supplyChainConsignment") or {}
            if supplyChainConsignment:
                exporter = supplyChainConsignment.get("exporter") or {}
                if exporter:
                    doc.exporter, created = Party.objects.get_or_create(
                        created_by_org=doc.created_by_org,
                        business_id=exporter.get("id"),
                        type=Party.TYPE_TRADER,
                        country=doc.sending_jurisdiction,
                        defaults={
                            "name": exporter.get("name") or "",
                        }
                    )
            issuer = data.get("issuer")
            if issuer:
                doc.issuer, created = Party.objects.get_or_create(
                    created_by_org=doc.created_by_org,
                    business_id=issuer.get("id"),
                    country=doc.sending_jurisdiction,
                    defaults={
                        "name": issuer.get("name") or "",
                    }
                )
            freeTradeAgreement = data.get("freeTradeAgreement")
            if freeTradeAgreement:
                try:
                    doc.fta = FTA.objects.get(name=freeTradeAgreement)
                except Exception:
                    logger.warning(
                        "The FTA %s is passed in the inbound document but can't be found locally",
                        freeTradeAgreement
                    )
            importer = data.get("importer", {})
            if importer and isinstance(importer, dict):
                importer_name = importer.get("name")
                doc.importer_name = importer_name

        except Exception as e:
            logger.exception(e)

    def _process_oa3_document(self, doc: Document, data: dict):
        return self._complain_and_die(
            doc,
            "Sorry, we don't support OAv3 documents yet",
        )

    def _complain_and_die(self, doc: Document, message, *message_args):
        logger.info(message, *message_args)
        DocumentHistoryItem.objects.create(
            type="error", document=doc,
            message=message % message_args,
        )
        return False
