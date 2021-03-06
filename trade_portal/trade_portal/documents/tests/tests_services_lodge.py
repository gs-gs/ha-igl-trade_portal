import json
from unittest import mock

import pytest
from django.conf import settings

from trade_portal.documents.models import Document, DocumentHistoryItem
from trade_portal.documents.services.lodge import DocumentService
from trade_portal.documents.tests.factories import DocumentFactory


class MockResponse(mock.MagicMock):
    def json(self):
        return self.json_resp

    @property
    def content(self):
        return json.dumps(self.json_resp).encode("utf-8")


@pytest.mark.django_db
@pytest.mark.parametrize("ERROR_CODE", [None, "wrap_500", "fail_notarize"])
@mock.patch("trade_portal.documents.tasks.document_oa_verify.apply_async")
@mock.patch("trade_portal.documents.services.lodge.NotaryService")
def test_document_service(notary_service_mock, oa_task_mock, docapi_env, ERROR_CODE):
    mockedJsonResp = {
        "1": "2",
        "signature": {
            "merkleRoot": "the only required field for the code, everything else is just proxied"
        }
    }

    ig_client = mock.MagicMock()
    oa_client = mock.MagicMock()
    oa_client.wrap_document.return_value = MockResponse(
        status_code=500 if ERROR_CODE == "wrap_500" else 200,
        json_resp=mockedJsonResp if ERROR_CODE != "wrap_500" else {}
    )
    notary_service_mock.notarize_file.return_value = True if ERROR_CODE != "fail_notarize" else False

    s = DocumentService(ig_client=ig_client, oa_client=oa_client)
    doc = DocumentFactory(
        status=Document.STATUS_NOT_SENT,
        verification_status=Document.V_STATUS_PENDING,
        workflow_status=Document.WORKFLOW_STATUS_ISSUED
    )

    issue_result = s.issue(doc)

    if ERROR_CODE is None:
        assert issue_result is True

        assert doc.status == Document.STATUS_NOT_SENT  # because IGL message not needed here, no recipient
        assert doc.verification_status == Document.V_STATUS_PENDING
        assert doc.workflow_status == Document.WORKFLOW_STATUS_ISSUED

        assert notary_service_mock.notarize_file.call_count == 1
        notary_service_mock.notarize_file.assert_called_once_with(
            "{}.{}.{}".format(
                settings.ICL_APP_COUNTRY.upper(),
                (doc.created_by_org.business_id).replace(".", "-"),
                doc.short_id,
            ),
            json.dumps(mockedJsonResp)
        )
        assert oa_task_mock.call_count == 1
        oa_task_mock.assert_called_once_with(
            args=[doc.pk], countdown=30
        )
        assert oa_client.wrap_document.call_count == 1
        assert DocumentHistoryItem.objects.count() == 5
        assert DocumentHistoryItem.objects.filter(document=doc).count() == 5
    elif ERROR_CODE == "wrap_500":
        assert issue_result is False
        assert doc.status == Document.STATUS_FAILED
        assert doc.verification_status == Document.V_STATUS_ERROR
        assert doc.workflow_status == Document.WORKFLOW_STATUS_NOT_ISSUED
        assert notary_service_mock.notarize_file.call_count == 0
        assert oa_client.wrap_document.call_count == 1
        assert oa_task_mock.call_count == 0
    elif ERROR_CODE == "fail_notarize":
        assert issue_result is True
        assert notary_service_mock.notarize_file.call_count == 1
        assert oa_client.wrap_document.call_count == 1
        assert oa_task_mock.call_count == 0
        assert (doc.status, doc.verification_status, doc.workflow_status) == (
            Document.STATUS_NOT_SENT,
            Document.V_STATUS_ERROR,
            Document.WORKFLOW_STATUS_ISSUED
        )
