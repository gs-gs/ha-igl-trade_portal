from django import forms

from .models import Document, FTA


class DocumentCreateForm(forms.ModelForm):

    class Meta:
        model = Document
        fields = (
            'type',
            'document_number', 'fta', 'importing_country', 'exporter',
            'importer_name',
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
        return super().save(*args, **kwargs)


class DocumentUpdateForm(DocumentCreateForm):
    pass
