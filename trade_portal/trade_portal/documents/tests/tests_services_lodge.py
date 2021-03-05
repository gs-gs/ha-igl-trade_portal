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


@pytest.mark.django_db
@mock.patch("trade_portal.documents.tasks.document_oa_verify.apply_async")
@mock.patch("requests.post")
@mock.patch("trade_portal.documents.services.lodge.NotaryService")
def test_document_service(notary_service_mock, post_mock, oa_task_mock, docapi_env):
    ig_client = mock.MagicMock()
    oa_client = mock.MagicMock()
    oa_client.wrap_document.return_value = MockResponse(status_code=200, json_resp={'wrapped': "body"})
    notary_service_mock.notarize_document.return_value = True

    s = DocumentService(ig_client=ig_client, oa_client=oa_client)
    doc = DocumentFactory(
        status=Document.STATUS_NOT_SENT,
        verification_status=Document.V_STATUS_PENDING,
        workflow_status=Document.WORKFLOW_STATUS_ISSUED
    )

    assert s.issue(doc) is True

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
        json.dumps({'wrapped': "body"})
    )
    assert oa_task_mock.call_count == 1
    oa_task_mock.assert_called_once_with(
        args=[doc.pk], countdown=30
    )
    assert post_mock.call_count == 0  # ensure it wasn't called because we have patched it
    assert oa_client.wrap_document.call_count == 1  # this was

    assert DocumentHistoryItem.objects.count() == 5
    assert DocumentHistoryItem.objects.filter(document=doc).count() == 5
