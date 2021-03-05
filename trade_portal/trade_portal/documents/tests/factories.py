import factory
from factory import DjangoModelFactory

from trade_portal.documents.models import OaDetails, Document, Party
from trade_portal.users.models import Organisation


class PartyFactory(DjangoModelFactory):
    type = Party.TYPE_CHAMBERS
    clear_business_id = "12345678901"
    bid_prefix = "abr.gov.au:abn"
    business_id = "abr.gov.au:abn::12345678901"
    name = factory.Sequence('Party-x-{0}'.format)
    country = "AU"

    class Meta:
        model = Party


class DocumentFactory(DjangoModelFactory):
    type = Document.TYPE_NONPREF_COO  # To avoid FTA mocking
    document_number = factory.Sequence('XX-TDC-{0}'.format)
    sending_jurisdiction = "AU"
    importing_country = "SG"
    importer_name = factory.Sequence('Receiver-x-{0}'.format)

    class Meta:
        model = Document

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        org = Organisation.objects.first()
        user = org.users.first()
        kwargs["oa"] = OaDetails.retrieve_new(for_org=org)
        kwargs["created_by_org"] = org
        kwargs["created_by_user"] = user
        kwargs["issuer"] = PartyFactory(created_by_user=user, created_by_org=org)

        if cls._meta.django_get_or_create:
            doc = cls._get_or_create(model_class, *args, **kwargs)
        else:
            doc = manager.create(*args, **kwargs)
        return doc
