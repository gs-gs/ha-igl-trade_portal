from unittest.mock import patch

import pytest
from django.urls import reverse

from trade_portal.documents.models import Document, DocumentFile


@pytest.mark.parametrize("ISSUE_TYPE", ["issue", "issue-without-qr-code"])
@pytest.mark.django_db
def test_document_issue(normal_user, ftas, ISSUE_TYPE):
    assert Document.objects.count() == 0
    nr = normal_user.web_client.get(reverse('documents:list'))
    assert nr.status_code == 200

    nr = normal_user.web_client.get(reverse('documents:create', args={"dtype": "non_pref_coo"}))

    # is it valid redirect?
    assert nr.status_code == 302
    assert nr.url.startswith("/documents/create-dtype/")
    assert len(nr.url) == len("/documents/create-dtype/fee3b66f-8276-4348-b145-40c627c1154d/")

    create_url = nr.url

    nr = normal_user.web_client.get(create_url)
    assert nr.status_code == 200
    assert nr.context.get("form").__class__.__name__ == "DocumentCreateForm"

    with open('/app/trade_portal/documents/tests/assets/A5.pdf', 'rb') as fp:
        nr = normal_user.web_client.post(
            create_url,
            {'file': fp}
        )

    assert nr.status_code == 302
    assert nr.url.endswith("/fill/")
    assert len(nr.url) == len("/documents/c617c471-06b2-41a8-94ff-7994a8ea11f9/fill/")

    fill_url = nr.url
    nr = normal_user.web_client.get(fill_url)
    assert nr.status_code == 200
    assert nr.context.get("form").__class__.__name__ == "DraftDocumentUpdateForm"

    assert Document.objects.count() == 1
    assert DocumentFile.objects.count() == 1

    doc = Document.objects.first()

    df = DocumentFile.objects.first()
    assert df.is_watermarked is False
    assert df.size == 7379  # bytes, test PDF size

    nr = normal_user.web_client.post(
        fill_url,
        {
            'document_number': "TestDocument123",
            'importing_country': "SG",
            'exporter': "51 824 753 556",
            'importer_name': "",
            'consignment_ref_doc_number': "",
        }
    )
    assert nr.status_code == 302, nr.context["form"].errors
    assert nr.url.endswith("/issue/")

    issue_url = nr.url

    nr = normal_user.web_client.get(issue_url)
    assert nr.status_code == 200
    assert nr.context["IS_PDF_ENCRYPTED"] is False
    assert nr.context["IS_PDF_UNPARSEABLE"] is False
    assert nr.context["SHOW_QR_CODE_ATTACHMENT"] is True
    assert not nr.context["data_warnings"]

    with patch('trade_portal.documents.tasks.lodge_document.apply_async') as mock_task:
        # we test lodge_document in a separate unit-test, so just ensure it's called
        nr = normal_user.web_client.post(
            issue_url,
            {
                # 'issue': "Issue",
                ISSUE_TYPE: "Issue",  # with or without QR code
                'qr_x': "50",
                'qr_y': "50",
            }
        )
        assert nr.status_code == 302
        assert nr.url == reverse("documents:detail", kwargs={"pk": doc.pk})
        assert mock_task.call_count == 1
        doc = Document.objects.first()
        assert doc.workflow_status == Document.WORKFLOW_STATUS_ISSUED
        assert doc.get_pdf_attachment().is_watermarked == (False if ISSUE_TYPE == "issue" else None)


@pytest.mark.django_db
def test_document_file_download_view(normal_user, ftas):
    nr = normal_user.web_client.get(reverse('documents:create', args={"dtype": "non_pref_coo"}))
    # is it valid redirect?
    assert nr.status_code == 302
    create_url = nr.url
    with open('/app/trade_portal/documents/tests/assets/A5.pdf', 'rb') as fp:
        nr = normal_user.web_client.post(
            create_url,
            {'file': fp}
        )
    assert nr.status_code == 302

    doc = Document.objects.first()
    docfile = DocumentFile.objects.first()

    # The document rendered as PNG
    nr = normal_user.web_client.get(
        reverse("documents:file-download", args=[doc.pk, docfile.pk]) + "?as_png=1"
    )
    assert nr.status_code == 200
    assert nr["Content-Type"] == "image/png"
    assert int(nr["Content-Length"]) > 50000   # it's 62238 now but may change in the future, any large value is fine

    # The document rendered as PNG
    nr = normal_user.web_client.get(
        reverse("documents:pdf-download", args=[doc.pk])
    )
    assert nr.status_code == 200
    assert nr["Content-Type"] == "application/pdf"
    with open('/app/trade_portal/documents/tests/assets/A5.pdf', 'rb') as fp:
        # exactly the same file it returns
        assert fp.read() == nr.content
