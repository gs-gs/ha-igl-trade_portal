from django import forms
from django.conf import settings

from trade_portal.legi.abr import fetch_abn_info

from .models import Party, Document, DocumentHistoryItem, DocumentFile, FTA


class DocumentCreateForm(forms.ModelForm):
    file = forms.FileField()
    exporter = forms.CharField(
        label=f"Exporter or manufacturer {settings.BID_NAME}",
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
        self._prepare_fields()

    def _prepare_fields(self):
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
            "The list is limited to the trade agreements entered in the system"
        )
        self.fields["importer_name"].label = "Importer Name (if known)"
        self.fields["importer_name"].help_text = ""
        self.fields["consignment_ref_doc_type"].widget.attrs["class"] = "form-control"
        self.fields["exporter"].widget.attrs["class"] = "form-control"

        if self.dtype == Document.TYPE_NONPREF_COO:
            del self.fields['fta']

            all_active_countries = set()
            for fta in FTA.objects.all():
                for c in fta.country:
                    all_active_countries.add(c)

            self.fields['importing_country'].choices = (
                (c.code, c.name) for c in all_active_countries
            )
        else:
            self.fields['fta'].label = False

        self.fields['document_number'].label = False
        self.fields['importing_country'].label = False
        self.fields['importer_name'].label = False
        self.fields['invoice_number'].label = False
        self.fields['origin_criteria'].label = False

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
                "type": Party.TYPE_TRADER,
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
                    Party.TYPE_TRADER
                    if self.current_org.is_trader
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

        return result


class DraftDocumentUpdateForm(DocumentCreateForm):

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.current_org = kwargs.pop('current_org')
        super(DocumentCreateForm, self).__init__(*args, **kwargs)
        self.dtype = self.instance.type
        self._prepare_fields()
        del self.fields["file"]
        self.initial['exporter'] = self.instance.exporter.business_id
        self.fields["exporter"].initial = self.instance.exporter.business_id

    def save(self, *args, **kwargs):
        return super(DocumentCreateForm, self).save(*args, **kwargs)


class ConsignmentSectionUpdateForm(forms.ModelForm):
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
            'consignment_ref_doc_number',
            'consignment_ref_doc_type',
            'consignment_ref_doc_issuer',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["consignment_ref_doc_type"].widget.attrs["class"] = "form-control"
