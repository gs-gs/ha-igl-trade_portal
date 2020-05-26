from django import forms

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

    class Meta:
        model = Document
        fields = (
            'type',
            'document_number', 'fta', 'issuer', 'importing_country', 'exporter',
            'importer_name', 'file',
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

        self.fields["exporter"].queryset = Party.objects.filter(
            created_by_org=self.current_org,
            type=Party.TYPE_EXPORTER
        )

        self.fields["issuer"].queryset = Party.objects.filter(
            created_by_org=self.current_org,
        )

        importers_added = Party.objects.filter(
            created_by_org=self.current_org,
            type=Party.TYPE_IMPORTER,
        )
        if importers_added:
            self.fields["importer_name"].help_text = "For example: " + ', '.join(
                importers_added.values_list("name", flat=True)
            )

    def save(self, *args, **kwargs):
        self.instance.created_by_user = self.user
        self.instance.created_by_org = self.current_org
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
