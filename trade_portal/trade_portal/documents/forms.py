from django import forms
from django.conf import settings

from trade_portal.legi.abr import fetch_abn_info

from .tasks import lodge_document
from .models import Party, Document, DocumentHistoryItem, DocumentFile, FTA


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
    exporter = forms.CharField(
        label=f"Exporter {settings.BID_NAME}",
        max_length=32, help_text=(
            "Please enter 11-digit ABN"
        ) if settings.BID_NAME == "ABN" else "Please enter 8 digits + letter"
    )
    consignment_ref_doc_issuer = forms.CharField(
        label=f"Document Issuer {settings.BID_NAME}",
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Consignment doc issuer'}
        ),
        required=False
    )
    consignment_ref_doc_number = forms.CharField(
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        ),
        required=False
    )

    class Meta:
        model = Document
        fields = (
            'document_number', 'fta', 'importing_country', 'exporter',
            'importer_name',
            'file',
            'consignment_ref_doc_number', 'consignment_ref_doc_type', 'consignment_ref_doc_issuer',

            'invoice_number', 'origin_criteria',
        )

    def __init__(self, *args, **kwargs):
        self.oa = kwargs.pop('oa')
        self.dtype = kwargs.pop('dtype')
        self.user = kwargs.pop('user')
        self.current_org = kwargs.pop('current_org')
        super().__init__(*args, **kwargs)
        self.instance.type = self.dtype
        self.fields["origin_criteria"].choices = [
            ('', 'Please Select Origin Criteria...'),
        ] + self.fields["origin_criteria"].choices[1:]

        self.fields["consignment_ref_doc_type"].choices = [
            ('', 'Please Select Document Type...'),
        ] + self.fields["consignment_ref_doc_type"].choices[1:]

        self.fields["fta"].empty_label = 'Please Select FTA...'

        self.fields['importing_country'].choices = []
        for fta in FTA.objects.all():
            for country in fta.country:
                self.fields['importing_country'].choices.append(
                    (country, f"{country.name} ({fta.name})")
                )
        self.fields['importing_country'].help_text = (
            "Countries list is limited to the trade agreements entered in the system"
        )
        self.fields["importer_name"].label = "Importer Name (if known)"
        self.fields["consignment_ref_doc_type"].widget.attrs["class"] = "form-control"
        self.fields["exporter"].widget.attrs["class"] = "form-control"

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
        if not value:
            raise forms.ValidationError("Please enter this value")
        if settings.BID_NAME == "ABN":
            if len(value) != 11:
                raise forms.ValidationError("The value must be 11 digits")
            exporter_data = fetch_abn_info(value)
            if not exporter_data or not exporter_data.get("Abn"):
                raise forms.ValidationError("Please provide a valid ABN in this field")
        else:
            exporter_data = {}
        exporter_party, created = Party.objects.get_or_create(
            business_id=value,
            created_by_org=self.current_org,
            defaults={
                "created_by_user": self.user,
                "name": exporter_data.get("EntityName") or "",
                "type": Party.TYPE_EXPORTER,
                "country": settings.ICL_APP_COUNTRY,
            }
        )
        return exporter_party

    def save(self, *args, **kwargs):
        self.instance.oa = self.oa
        self.instance.type = self.dtype
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
                "dot_separated_id": self.current_org.dot_separated_id,
            }
        )
        self.instance.issuer = issuer_party

        if self.instance.consignment_ref_doc_type not in ("ConNote", "HouseBill"):
            self.instance.consignment_ref_doc_issuer = ""

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

        DocumentHistoryItem.objects.create(
            type="message",
            document=result,
            message=f"The document has been created by {self.user}",
        )

        lodge_document.apply_async(
            [result.pk],
            countdown=2
        )
        return result


# class DocumentUpdateForm(DocumentCreateForm):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields["file"].required = False
#         self.fields["file"].help_text = "Leave empty if you want to keep the old file"
#         del self.fields["exporter"]
#         del self.fields["type"]
