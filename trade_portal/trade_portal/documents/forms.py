from django import forms
from django.conf import settings

from trade_portal.legi.abr import fetch_abn_info

from .models import Party, Document, DocumentFile, FTA


class PartyCreateForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = (
            'type',
            'business_id', 'name', 'country',
        )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.current_org = kwargs.pop('current_org')
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.instance.created_by_user = self.user
        self.instance.created_by_org = self.current_org
        return super().save(*args, **kwargs)


class PartyUpdateForm(PartyCreateForm):
    def save(self, *args, **kwargs):
        # don't update created_by_* parameters
        return super(PartyCreateForm, self).save(*args, **kwargs)


class DocumentCreateForm(forms.ModelForm):
    file = forms.FileField()
    exporter = forms.CharField(max_length=32, help_text="Please enter 11-digit ABN")

    class Meta:
        model = Document
        fields = (
            'type',
            'document_number', 'fta', 'importing_country', 'exporter',
            'importer_name',
            'file',
            'consignment_ref_doc_number', 'consignment_ref_doc_type', 'consignment_ref_doc_issuer',

            'invoice_number', 'origin_criteria',
        )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.current_org = kwargs.pop('current_org')
        super().__init__(*args, **kwargs)

        self.fields['importing_country'].choices = []
        for fta in FTA.objects.all():
            for country in fta.country:
                self.fields['importing_country'].choices.append(
                    (country, f"{country.name} ({fta.name})")
                )
        self.fields['importing_country'].help_text = (
            "Countries list is limited to the trade agreements entered in the system"
        )

        importers_added = Party.objects.filter(
            created_by_org=self.current_org,
            type=Party.TYPE_IMPORTER,
        )
        if importers_added:
            self.fields["importer_name"].help_text = "For example: " + ', '.join(
                importers_added.exclude(name="").values_list("name", flat=True)
            )

    def clean_exporter(self):
        value = self.cleaned_data.get("exporter").strip().replace(" ", "")
        if not value or len(value) != 11:
            raise forms.ValidationError("The value must be 11 digits")
        exporter_data = fetch_abn_info(value)
        if not exporter_data or not exporter_data.get("Abn"):
            raise forms.ValidationError("Please provide a valid ABN in this field")
        exporter_party, created = Party.objects.get_or_create(
            business_id=exporter_data["Abn"],
            created_by_org=self.current_org,
            defaults={
                "created_by_user": self.user,
                "name": exporter_data["EntityName"],
                "type": Party.TYPE_EXPORTER,
                "country": settings.ICL_APP_COUNTRY,
            }
        )
        return exporter_party

    def save(self, *args, **kwargs):
        self.instance.created_by_user = self.user
        self.instance.created_by_org = self.current_org

        # filling the issuer field: current org converted to party
        issuer_party, created = Party.objects.get_or_create(
            created_by_org=self.current_org,
            business_id=self.current_org.business_id,
            name=self.current_org.name,
            country=settings.ICL_APP_COUNTRY,
            defaults={
                "created_by_user": self.user,
                "type": (
                    Party.TYPE_EXPORTER
                    if self.current_org.type == self.current_org.TYPE_EXPORTER
                    else Party.TYPE_CHAMBERS
                ),
            }
        )
        self.instance.issuer = issuer_party

        result = super().save(*args, **kwargs)
        uploaded_file = self.cleaned_data.get("file")
        if uploaded_file:
            DocumentFile.objects.filter(
                doc=self.instance
            ).delete()
            df = DocumentFile(
                doc=self.instance,
                size=uploaded_file.size,
                file=uploaded_file,
                filename=uploaded_file.name,
                created_by=self.user,
            )
            df.save()
        return result


class DocumentUpdateForm(DocumentCreateForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file"].required = False
        self.fields["file"].help_text = "Leave empty if you want to keep the old file"
        del self.fields["exporter"]
