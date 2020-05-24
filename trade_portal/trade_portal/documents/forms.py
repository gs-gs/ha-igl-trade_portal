from django import forms

from .models import Document, DocumentFile, FTA


class DocumentCreateForm(forms.ModelForm):
    file = forms.FileField()

    class Meta:
        model = Document
        fields = (
            'type',
            'document_number', 'fta', 'importing_country', 'exporter',
            'importer_name', 'file',
        )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
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

    def save(self, *args, **kwargs):
        self.instance.created_by = self.user
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
