import base64
import collections
from rest_framework import serializers

from trade_portal.documents.models import Document, FTA


def dict_merge(dct, merge_dct):
    """
    Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :return: None
    """
    for k, v in merge_dct.items():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.Mapping)):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]


class CertificateSerializer(serializers.Serializer):

    class Meta:
        model = Document
        fields = (
            'id', 'name',
        )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.org = kwargs.pop("org")
        super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        """
        We just proxy the model's raw_certificate_data, replacing some
        critical fields by the our-generated values (so users don't invent
        their own IDs for example)
        """
        data = instance.raw_certificate_data.copy()
        data.update({
            "id": instance.pk,
        })
        data["certificateOfOrigin"].update({
            "issueDateTime": instance.created_at,
            "isPreferential": instance.type == Document.TYPE_PREF_COO,
            "exportCountry": str(instance.sending_jurisdiction),
            "importCountry": str(instance.importing_country),
        })
        attachments = []
        for file in instance.files.all():
            rendered = file.metadata.copy()
            rendered.update({
                "filename": file.filename,
                "type": file.mimetype(),
                "data": base64.b64encode(file.file.read()).decode("utf-8")
            })
            attachments.append(rendered)
        data['certificateOfOrigin']['attachments'] = attachments
        return data

    def validate(self, data):
        cert_data = data["raw_certificate_data"].get("certificateOfOrigin")
        if not self.instance and "freeTradeAgreement" not in cert_data:
            raise serializers.ValidationError({"freeTradeAgreement": "Required field"})
        if "freeTradeAgreement" in cert_data:
            if not FTA.objects.filter(name=cert_data["freeTradeAgreement"]).exists():
                raise serializers.ValidationError({"freeTradeAgreement": "Doesn't exist in the system"})
        return data

    def to_internal_value(self, data):
        """
        Proxy the certificate data (raw, mostly unparsed) to the
        instance's "raw_certificate_data" field, picking out something
        insteresting to us
        """
        super().to_internal_value(data)  # just to run the validations
        ret = {
            "raw_certificate_data": data,
        }
        if not self.instance or not self.instance.pk:
            cert_data = data.get("certificateOfOrigin") or {}
            supplyChainConsignment = cert_data.get("supplyChainConsignment", {})
            ret.update({
                "type": (
                    Document.TYPE_PREF_COO
                    if cert_data.get("isPreferential")
                    else Document.TYPE_NONPREF_COO
                ),
                "document_number": cert_data.get("name"),
                "sending_jurisdiction": supplyChainConsignment.get("exportCountry"),
                "importing_country": supplyChainConsignment.get("importCountry"),
            })
        return ret

    def create(self, validated_data):
        create_kwargs = validated_data.copy()
        create_kwargs.pop("id", None)
        create_kwargs["created_by_user"] = self.user
        create_kwargs["created_by_org"] = self.org

        # some business logic - propagating some fields to the model instance
        cert_data = validated_data["raw_certificate_data"]["certificateOfOrigin"]
        if "freeTradeAgreement" in cert_data:
            create_kwargs["fta"] = FTA.objects.filter(
                name=cert_data["freeTradeAgreement"]
            ).first()

        obj = Document.objects.create(
            **create_kwargs
        )
        return obj

    def update(self, instance, validated_data):
        dict_merge(instance.raw_certificate_data, validated_data["raw_certificate_data"])
        cert_data = validated_data["raw_certificate_data"].get("certificateOfOrigin") or {}
        if "name" in cert_data:
            instance.document_number = cert_data["name"]
        if "freeTradeAgreement" in cert_data:
            fta = FTA.objects.filter(
                name=cert_data["freeTradeAgreement"]
            ).first()
            if fta:
                instance.fta = fta
            else:
                raise Exception("Unknown FTA")
        instance.save()
        return instance
